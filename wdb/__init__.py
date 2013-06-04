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

from ._compat import execute
from .ui import Interaction, dump
from io import StringIO
from cgi import escape
from contextlib import contextmanager
from linecache import checkcache, getlines, getline
from log_colorizer import get_color_logger
from multiprocessing.connection import Client
from breakpoint import (
    Breakpoint, LineBreakpoint,
    ConditionalBreakpoint, FunctionBreakpoint)
from uuid import uuid4
import dis
import os
import sys
import threading
import webbrowser
import atexit


BASE_PATH = os.path.join(
    os.path.abspath(os.path.dirname(__file__)))
RES_PATH = os.path.join(BASE_PATH, 'resources')

log = get_color_logger('wdb')
log.setLevel(30)


class Wdb(object):
    """Wdb debugger main class"""
    _instances = {}
    _sockets = []
    enabled = True

    @staticmethod
    def get():
        thread = threading.current_thread()
        wdb = Wdb._instances.get(thread)
        if not wdb:
            wdb = Wdb()
            wdb.thread = thread
            Wdb._instances[thread] = wdb
        return wdb

    @staticmethod
    def pop():
        thread = threading.current_thread()
        Wdb._instances.pop(thread)

    def __init__(self):
        self.obj_cache = {}
        self.begun = False
        self.connected = False
        self.stepping = False
        self.extra_vars = {}
        self.last_obj = None
        self.break_on_file = None
        self.reset()
        self.uuid = str(uuid4())
        self.breaks = set()
        self.connect()

    def run_file(self, filename):
        import __main__
        __main__.__dict__.clear()
        __main__.__dict__.update({
            "__name__": "__main__",
            "__file__": filename,
            "__builtins__": __builtins__,
        })
        with open(filename, "rb") as fp:
            statement = "exec(compile(%r, %r, 'exec'))" % (
                fp.read(), filename)
        self.run(statement, filename)

    def run(self, cmd, fn, globals=None, locals=None):
        if globals is None:
            import __main__
            globals = __main__.__dict__
        if locals is None:
            locals = globals
        self.reset()
        if isinstance(cmd, str):
            cmd = compile(cmd, "<string>", "exec")
        self.start_trace()
        self.break_on_file = fn
        try:
            execute(cmd, globals, locals)
        finally:
            self.stop_trace()

    def reset(self):
        import linecache
        linecache.checkcache()
        self.botframe = None
        self._set_stopinfo(None, None)

    def connect(self):
        log.info('Connecting socket')
        self._socket = Client(('localhost', 19840))
        Wdb._sockets.append(self._socket)
        self._socket.send_bytes(self.uuid.encode('utf-8'))

    def trace_dispatch(self, frame, event, arg):
        if event == 'line':
            return self.dispatch_line(frame)
        if event == 'call':
            return self.dispatch_call(frame, arg)
        if event == 'return':
            return self.dispatch_return(frame, arg)
        if event == 'exception':
            return self.dispatch_exception(frame, arg)
        if event == 'c_call':
            return self.trace_dispatch
        if event == 'c_exception':
            return self.trace_dispatch
        if event == 'c_return':
            return self.trace_dispatch
        self.log.warn(
            'Unknown debugging event: %r' % event)
        return self.trace_dispatch

    def start_trace(self, full=False, frame=None, below=False):
        """Make an instance of Wdb and trace all code below"""
        sys.settrace(None)
        log.info('Starting trace on %r' % self.thread)
        start_frame = frame or sys._getframe().f_back

        iter_frame = start_frame
        while iter_frame:
            del iter_frame.f_trace
            iter_frame = iter_frame.f_back

        self.reset()

        def trace(frame, event, arg):
            if below:
                if frame == start_frame:
                    return trace
                elif frame.f_back == start_frame:
                    self.stop_frame = frame
            if (self.break_on_file and
                    frame.f_code.co_filename == self.break_on_file):
                self.stopframe = frame
                self.stoplineno = frame.f_code.co_firstlineno
                self.break_on_file = None
            rv = self.trace_dispatch(frame, event, arg)
            fn = frame.f_code.co_filename
            if (rv is None and not
                full and
                (fn == os.path.abspath(fn) or fn.startswith('<')) and not
                fn.startswith(
                    os.path.dirname(os.path.abspath(sys.argv[0])))):
                return

            return trace

        # Stop frame is the calling one
        self.stoplineno = -1
        self.stopframe = start_frame
        # self.botframe = None
        iter_frame = start_frame
        while iter_frame:
            iter_frame.f_trace = trace
            self.botframe = iter_frame
            iter_frame = iter_frame.f_back

        # Set trace with wdb
        sys.settrace(trace)

    def set_trace(self, frame=None):
        """Start debugging from `frame`.

        If frame is not specified, debugging starts from caller's frame.
        """
        if frame is None:
            frame = sys._getframe().f_back
        self.reset()
        while frame:
            frame.f_trace = self.trace_dispatch
            self.botframe = frame
            frame = frame.f_back
        self.set_step()
        sys.settrace(self.trace_dispatch)

    def stop_trace(self, frame=None):
        self.tracing = False
        frame = frame or sys._getframe().f_back
        while frame and frame is not self.botframe:
            del frame.f_trace
            frame = frame.f_back
        sys.settrace(None)
        log.info('Stopping trace on  %r' % self.thread)

    def set_until(self, frame, lineno=None):
        """Stop when the line with the line no greater than the current one is
        reached or when returning from current frame"""
        # the name "until" is borrowed from gdb
        if lineno is None:
            lineno = frame.f_lineno + 1
        self._set_stopinfo(frame, frame, lineno)

    def set_step(self):
        """Stop after one line of code."""
        self._set_stopinfo(None, None)

    def set_next(self, frame):
        """Stop on the next line in or below the given frame."""
        self._set_stopinfo(frame, None)

    def set_return(self, frame):
        """Stop when returning from the given frame."""
        self._set_stopinfo(frame.f_back, frame)

    def set_continue(self):
        self.stopframe = self.botframe
        self._set_stopinfo(self.botframe, None, -1)

    def _set_stopinfo(self, stopframe, returnframe, stoplineno=0):
        self.stopframe = stopframe
        self.returnframe = returnframe
        self.stoplineno = stoplineno

    def set_break(self, filename, lineno=None, temporary=False, cond=None,
                  funcname=None):
        if lineno:
            if cond:
                breakpoint = ConditionalBreakpoint(
                    filename, lineno, cond, temporary)
            else:
                breakpoint = LineBreakpoint(filename, lineno, cond, temporary)
        elif funcname:
            breakpoint = FunctionBreakpoint(filename, funcname, temporary)
        else:
            breakpoint = Breakpoint(filename, temporary)
        self.breaks.add(breakpoint)

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

    def get_stack(self, f, t):
        stack = []
        if t and t.tb_frame is f:
            t = t.tb_next
        while f is not None:
            stack.append((f, f.f_lineno))
            if f is self.botframe:
                break
            f = f.f_back
        stack.reverse()
        i = max(0, len(stack) - 1)
        while t is not None:
            stack.append((t.tb_frame, t.tb_lineno))
            t = t.tb_next
        if f is None:
            i = max(0, len(stack) - 1)
        return stack, i

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
        log.debug('Sending %s' % data)
        self._socket.send_bytes(data.encode('utf-8'))

    def receive(self):
        """Receive data through websocket"""
        log.debug('Receiving')
        data = self._socket.recv_bytes()
        log.debug('Got %s' % data)
        return data.decode('utf-8')

    def interaction(
            self, frame, tb=None,
            exception='Wdb', exception_description='Stepping',
            init=None):
        """User interaction handling blocking on socket receive"""
        log.info('Interaction for %r -> %r %r %r %r' % (
            self.thread, frame, tb, exception, exception_description))
        self.stepping = True

        if not self.connected:
            log.debug('Launching browser and wait for connection')
            webbrowser.open(
                'http://localhost:1984/debug/session/%s' % self.uuid)
            self.connected = True

        interaction = Interaction(
            self, frame, tb, exception, exception_description, init=init)

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
            init = 'Echo|%s' % dump({
                'for': '__call__',
                'val': fun})
            self.interaction(
                frame, init=init,
                exception_description='Calling %s' % fun)

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
        fun = frame.f_code.co_name
        log.info('Returning from %r with value: %r' % (
            fun, return_value))
        init = 'Echo|%s' % dump({
            'for': '__return__',
            'val': return_value
        })
        self.interaction(
            frame, init=init,
            exception_description='Returning from %s with value %s' % (
                fun, return_value))

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
        init = 'Echo|%s' % dump({
            'for': '__exception__',
            'val': escape('%s: %s') % (
                exception, exception_description)})
        # User exception is 4 frames away from exception
        frame = frame or sys._getframe().f_back.f_back.f_back.f_back
        self.interaction(
            frame, tb, exception, exception_description, init=init)

    def stop_here(self, frame):
        if frame is self.stopframe:
            if self.stoplineno == -1:
                return False
            return frame.f_lineno >= self.stoplineno
        while frame is not None and frame is not self.stopframe:
            if frame is self.botframe:
                return True
            frame = frame.f_back
        return False

    def break_here(self, frame):
        for breakpoint in set(self.breaks):
            if breakpoint.breaks(frame):
                if breakpoint.temporary:
                    self.breaks.remove(breakpoint)
                return True
        return False

    def get_file_breaks(self, filename):
        return [breakpoint for breakpoint in self.breaks
                if breakpoint.on_file(filename)]

    def dispatch_line(self, frame):
        if self.stop_here(frame) or self.break_here(frame):
            self.user_line(frame)
        return self.trace_dispatch

    def dispatch_return(self, frame, arg):
        if self.stop_here(frame) or frame == self.returnframe:
            try:
                self.frame_returning = frame
                self.user_return(frame, arg)
            finally:
                self.frame_returning = None
        return self.trace_dispatch

    def dispatch_call(self, frame, arg):
        if not (self.stop_here(frame) or
                self.get_file_breaks(frame.f_code.co_filename)):
            return
        self.user_call(frame, arg)
        return self.trace_dispatch

    def dispatch_exception(self, frame, arg):
        """Always break on exception"""
        self.user_exception(frame, arg)
        return self.trace_dispatch


def set_trace(frame=None):
    """Set trace on current line, or on given frame"""
    frame = frame or sys._getframe().f_back
    wdb = Wdb.get()
    sys.settrace(None)
    # Clear previous tracing
    wdb.stop_trace()
    # Set trace to the top frame
    wdb.set_trace(frame)


def start_trace(full=False, frame=None, below=False):
    """Start tracing program at callee level
       breaking on exception/breakpoints"""
    wdb = Wdb.get()
    if not wdb.stepping:
        wdb.start_trace(full, frame or sys._getframe().f_back, below=below)


def stop_trace(frame=None, close_on_exit=False):
    """Start tracing program at callee level
       breaking on exception/breakpoints"""
    wdb = Wdb.get()
    if not wdb.stepping:
        wdb.stop_trace(frame or sys._getframe().f_back)
        if close_on_exit:
            wdb.send('Die')


@contextmanager
def trace(full=False, frame=None, below=False, close_on_exit=False):
    """Make a tracing context with `with trace():`"""
    # Contextmanager -> 2 calls to get here
    frame = frame or sys._getframe().f_back.f_back
    start_trace(full, frame, below)
    try:
        yield
    finally:
        stop_trace(frame, close_on_exit=close_on_exit)


@atexit.register
def cleanup():
    for socket in Wdb._sockets:
        socket.close()
