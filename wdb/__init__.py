# *-* coding: utf-8 *-*
from __future__ import with_statement
# This file is part of wdb
#
# wdb Copyright (C) 2012  Florian Mounier, Kozea
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from ._compat import parse_qs, Bdb, with_metaclass, to_bytes, execute
from .ui import Interaction, dump
from io import StringIO
from bdb import BdbQuit, Breakpoint
from cgi import escape
from contextlib import contextmanager
from linecache import checkcache, getlines, getline
from log_colorizer import get_color_logger
from mimetypes import guess_type
from multiprocessing.connection import Client
from random import randint, seed
from uuid import uuid4
import atexit
import dis
import os
import sys
import threading
import time
import traceback
import webbrowser

BASE_PATH = os.path.join(
    os.path.abspath(os.path.dirname(__file__)))
RES_PATH = os.path.join(BASE_PATH, 'resources')

log = get_color_logger('wdb')
log.setLevel(10)


class Wdb(Bdb):
    """Wdb debugger main class"""
    _instances = {}

    @staticmethod
    def get():
        wdb = Wdb._instances.get(threading.current_thread())
        if not wdb:
            wdb = Wdb()
            Wdb._instances[threading.current_thread()] = wdb
        return wdb

    @staticmethod
    def settrace(frame=None):
        sys.settrace(None)
        # Removing current global tracing function if any
        wdb = Wdb.get()
        frame = frame or sys._getframe().f_back
        # Clear previous tracing
        wdb.stop_trace()
        # Set trace to the top frame
        wdb.set_trace(frame)

    def __init__(self, skip=None):
        self.obj_cache = {}
        try:
            Bdb.__init__(self, skip=skip)
        except TypeError:
            Bdb.__init__(self)
        self.begun = False
        self.quitting = False
        self.connected = False
        self.extra_vars = {}
        self.last_obj = None
        self.reset()
        self.uuid = str(uuid4())

        breaks_per_file_lno = Breakpoint.bplist.values()
        for bps in breaks_per_file_lno:
            breaks = list(bps)
            for bp in breaks:
                args = bp.file, bp.line, bp.temporary, bp.cond
                self.set_break(*args)
                log.info('Resetting break %s' % repr(args))

        self.connect()

    @staticmethod
    def trace(full=False):
        """Make an instance of Wdb and trace all code below"""
        wdb = Wdb.get()
        sys.settrace(None)
        log.info('Tracing with an existing server')
        wdb.reset()
        wdb.stop_trace()
        wdb.begun = False

        def trace(frame, event, arg):
            rv = wdb.trace_dispatch(frame, event, arg)
            fn = frame.f_code.co_filename
            if (rv is None and not
                full and
                (fn == os.path.abspath(fn) or fn.startswith('<')) and not
                fn.startswith(
                    os.path.dirname(os.path.abspath(sys.argv[0])))):
                return

            return trace

        # Prepare full tracing
        frame = sys._getframe().f_back
        # Stop frame is the calling one
        wdb.stoplineno = -1
        wdb.stopframe = frame
        while frame:
            frame.f_trace = trace
            wdb.botframe = frame
            frame = frame.f_back

        # Set trace with wdb
        sys.settrace(trace)
        return wdb

    @staticmethod
    def run_file(filename):
        import __main__
        __main__.__dict__.clear()
        __main__.__dict__.update({
            "__name__": "__main__",
            "__file__": filename,
            "__builtins__": __builtins__,
        })
        __main__.__dict__['__builtins__']['wtf'] = set_trace
        with open(filename, "rb") as fp:
            statement = "exec(compile(%r, %r, 'exec'))" % \
                        (fp.read(), filename)
        Wdb.run(statement)

    @staticmethod
    def run(cmd, globals=None, locals=None):
        if globals is None:
            import __main__
            globals = __main__.__dict__
        if locals is None:
            locals = globals

        if isinstance(cmd, str):
            cmd = compile(cmd, "<string>", "exec")
        try:
            execute(cmd, globals, locals)
        except BdbQuit:
            pass

    def connect(self):
        self._socket = Client(('localhost', 18532))
        self._socket.send_bytes(self.uuid.encode('utf-8'))

    def stop_trace(self, threading_too=False):
        sys.settrace(None)
        frame = sys._getframe().f_back
        while frame and frame is not self.botframe:
            del frame.f_trace
            frame = frame.f_back
        if threading_too:
            threading.settrace(None)

    def set_continue(self):
        self._set_stopinfo(self.botframe, None, -1)

    def safe_repr(self, obj):
        """Like a repr but without exception"""
        try:
            return repr(obj)
        except Exception as e:
            return '??? Broken repr (%s: %s)' % (type(e).__name__, e)

    def safe_better_repr(self, obj):
        """Repr with inspect links on objects"""
        try:
            rv = self.better_repr(obj)
        except Exception:
            rv = None
        if rv:
            return rv

        self.obj_cache[id(obj)] = obj
        return '<a href="%d" class="inspect">%s</a>' % (
            id(obj), escape(repr(obj)))

    def better_repr(self, obj):
        """Repr with html decorations"""
        if isinstance(obj, dict):
            if type(obj) != dict:
                dict_repr = type(obj).__name__ + '({'
                closer = '})'
            else:
                dict_repr = '{'
                closer = '}'
            if len(obj) > 2:
                dict_repr += '<table>'
                dict_repr += ''.join([
                    '<tr><td>' + self.safe_repr(key) + '</td><td>:</td>'
                    '<td>' + self.safe_better_repr(val) + '</td></tr>'
                    for key, val in sorted(obj.items(), key=lambda x: x[0])])
                dict_repr += '</table>'
            else:
                dict_repr += ', '.join([
                    self.safe_repr(key) + ': ' + self.safe_better_repr(val)
                    for key, val in sorted(obj.items(), key=lambda x: x[0])])
            dict_repr += closer
            return dict_repr

        if any([
                isinstance(obj, list),
                isinstance(obj, set),
                isinstance(obj, tuple)]):
            if type(obj) == list:
                iter_repr = '['
                closer = ']'
            elif type(obj) == set:
                iter_repr = '{'
                closer = '}'
            elif type(obj) == tuple:
                iter_repr = '('
                closer = ')'
            else:
                iter_repr = escape(obj.__class__.__name__) + '(['
                closer = '])'

            splitter = ', '
            if len(obj) > 2:
                splitter += '\n'
                iter_repr += '\n'
                closer = '\n' + closer

            iter_repr += splitter.join(
                [self.safe_better_repr(val) for val in obj])

            iter_repr += closer
            return iter_repr

    @contextmanager
    def capture_output(self, with_hook=True):
        """Steal stream output, return them in string, restore them"""
        self.hooked = ''

        def display_hook(obj):
            # That's some dirty hack
            self.hooked += self.safe_better_repr(obj)
            self.last_obj = obj

        stdout, stderr = sys.stdout, sys.stderr
        if with_hook:
            d_hook = sys.displayhook
            sys.displayhook = display_hook

        sys.stdout, sys.stderr = StringIO(), StringIO()
        out, err = [], []
        try:
            yield out, err
        finally:
            out.extend(sys.stdout.getvalue().splitlines())
            err.extend(sys.stderr.getvalue().splitlines())
            if with_hook:
                sys.displayhook = d_hook

            sys.stdout, sys.stderr = stdout, stderr

    def dmp(self, thing):
        """Dump the content of an object in a dict for wdb.js"""

        def safe_getattr(key):
            """Avoid crash on getattr"""
            try:
                return getattr(thing, key)
            except Exception as e:
                return 'Error getting attr "%s" from "%s" (%s: %s)' % (
                    key, thing,
                    type(e).__name__, e)

        return dict(
            (escape(key), {
                'val': self.safe_better_repr(safe_getattr(key)),
                'type': type(safe_getattr(key)).__name__
            })
            for key in dir(thing)
        )

    def get_file(self, filename):
        """Get file source from cache"""
        checkcache(filename)
        return ''.join(getlines(filename))

    def get_trace(self, frame, tb, w_code=None):
        """Get a dict of the traceback for wdb.js use"""
        frames = []
        stack, current = self.get_stack(frame, tb)

        for i, (frame, lno) in enumerate(stack):
            code = frame.f_code
            filename = code.co_filename
            if filename == '<wdb>' and w_code:
                line = w_code
            else:
                checkcache(filename)
                line = getline(filename, lno, frame.f_globals)
                line = line and line.strip()

            startlnos = dis.findlinestarts(code)
            lastlineno = list(startlnos)[-1][1]
            frames.append({
                'file': filename,
                'function': code.co_name,
                'flno': code.co_firstlineno,
                'llno': lastlineno,
                'lno': lno,
                'code': line,
                'level': i
            })

        return stack, frames, current

    def send(self, data):
        """Send data through websocket"""
        log.info('Sending %s' % data)
        self._socket.send_bytes(data.encode('utf-8'))

    def receive(self):
        """Receive data through websocket"""
        log.info('Receiving')
        data = self._socket.recv_bytes()
        log.info('Got %s' % data)
        return data.decode('utf-8')

    def interaction(
            self, frame, tb=None,
            exception='Wdb', exception_description='Set Trace'):
        """User interaction handling blocking on socket receive"""

        log.debug('Interaction for %r %r %r %r' % (
            frame, tb, exception, exception_description))

        if not self.connected:
            log.info('Connectiong')
            webbrowser.open(
                'http://localhost:2560/debug/session/%s' % self.uuid)
            self.connected = True

        interaction = Interaction(
            self, frame, tb, exception, exception_description)

        # For meta debugging purpose
        self._ui = interaction

        if self.begun:
            # Each new state sends the trace and selects a frame
            interaction.init()
        else:
            self.begun = True
        interaction.loop()

    def user_call(self, frame, argument_list):
        """This method is called when there is the remote possibility
        that we ever need to stop in this function."""
        if self.stop_here(frame):
            fun = frame.f_code.co_name
            log.info('Calling: %r' % fun)
            self.send('Echo|%s' % dump({
                'for': '__call__',
                'val': fun}))
            self.interaction(frame)

    def user_line(self, frame):
        """This function is called when we stop or break at this line."""
        log.debug('LINE')
        log.info('Stopping at line %r:%d' % (
            frame.f_code.co_filename, frame.f_lineno))
        log.debug('User Line Interaction for %r' % frame)
        self.interaction(frame)

    def user_return(self, frame, return_value):
        """This function is called when a return trap is set here."""
        self.obj_cache[id(return_value)] = return_value
        self.extra_vars['__return__'] = return_value
        log.info('Returning from %r with value: %r' % (
            frame.f_code.co_name, return_value))
        self.send('Echo|%s' % dump({
            'for': '__return__',
            'val': return_value
        }))
        self.interaction(frame)

    def user_exception(self, frame, exc_info):
        """This function is called if an exception occurs,
        but only if we are to stop at or just below this level."""
        type_, value, tb = exc_info
        # Python 3 is broken see http://bugs.python.org/issue17413
        _value = value
        if not isinstance(_value, BaseException):
            _value = type_(value)
        fake_exc_info = type_,  _value, tb
        log.error('Exception during trace', exc_info=fake_exc_info)
        self.obj_cache[id(exc_info)] = exc_info
        self.extra_vars['__exception__'] = exc_info
        exception = type_.__name__
        exception_description = str(value)
        self.send('Echo|%s' % dump({
            'for': '__exception__',
            'val': escape('%s: %s') % (
                exception, exception_description)}))
        # User exception is 4 frames away from exception
        frame = frame or sys._getframe().f_back.f_back.f_back.f_back
        self.interaction(frame, tb, exception, exception_description)

    def do_clear(self, arg):
        """Breakpoint clearing implementation"""
        log.info('Closing %r' % arg)
        self.clear_bpbynumber(arg)

    def dispatch_exception(self, frame, arg):
        """Always break on exception (This is different from pdb behaviour)"""
        self.user_exception(frame, arg)
        if self.quitting:
            raise BdbQuit
        return self.trace_dispatch

    def _recursive(self, g, l):
        """Inspect wdb with pdb"""
        # Inspect curent debugger vars through pdb
        sys.settrace(None)
        from pdb import Pdb
        p = Pdb()
        sys.call_tracing(p.run, ('1/0', g, l))
        sys.settrace(self.trace_dispatch)
        self.lastcmd = p.lastcmd


def set_trace(frame=None):
    """Set trace on current line, or on given frame"""
    Wdb.settrace(frame or sys._getframe().f_back)
