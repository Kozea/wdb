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
__version__ = '1.0.2'

from ._compat import execute, StringIO

from .breakpoint import (
    Breakpoint, LineBreakpoint,
    ConditionalBreakpoint, FunctionBreakpoint)
from .ui import Interaction, dump
from .utils import pretty_frame
from .state import Running, Step, Next, Until, Return
from cgi import escape
from contextlib import contextmanager
from log_colorizer import get_color_logger
from multiprocessing.connection import Client
from uuid import uuid4
import dis
import os
import logging
import sys
import threading
import webbrowser
import atexit

# Get wdb server host
SOCKET_SERVER = os.getenv('WDB_SOCKET_SERVER', 'localhost')
# and port
SOCKET_PORT = int(os.getenv('WDB_SOCKET_PORT', '19840'))

# Get wdb web server host
WEB_SERVER = os.getenv('WDB_WEB_SERVER')
# and port
WEB_PORT = int(os.getenv('WDB_WEB_PORT', 0))

WDB_NO_BROWSER_AUTO_OPEN = bool(os.getenv('WDB_NO_BROWSER_AUTO_OPEN', False))

BASE_PATH = os.path.join(
    os.path.abspath(os.path.dirname(__file__)))
RES_PATH = os.path.join(BASE_PATH, 'resources')

log = get_color_logger('wdb')
trace_log = logging.getLogger('wdb.trace')

for log_name in ('main', 'trace', 'ui', 'ext', 'bp'):
    logging.getLogger(
        'wdb.%s' % log_name if log_name != 'main' else 'wdb'
    ).setLevel(
        getattr(logging,
                os.getenv(
                    'WDB_%s_LOG' % log_name.upper(),
                    os.getenv('WDB_LOG', 'WARN')).upper(),
                'WARN'))


class Wdb(object):
    """Wdb debugger main class"""
    _instances = {}
    _sockets = []
    enabled = True
    breakpoints = set()

    @staticmethod
    def get(no_create=False):
        """Get the thread local singleton"""
        pid = os.getpid()
        thread = threading.current_thread()
        wdb = Wdb._instances.get((pid, thread))
        if not wdb and not no_create:
            wdb = object.__new__(Wdb)
            Wdb.__init__(wdb)
            wdb.pid = pid
            wdb.thread = thread
            Wdb._instances[(pid, thread)] = wdb
        return wdb

    @staticmethod
    def pop():
        """Remove instance from instance list"""
        pid = os.getpid()
        thread = threading.current_thread()
        Wdb._instances.pop((pid, thread))

    def __new__(cls):
        return cls.get()

    def __init__(self):
        log.debug('New wdb instance %r' % self)
        self.obj_cache = {}
        self.tracing = False
        self.begun = False
        self.connected = False
        self.stepping = False
        self.extra_vars = {}
        self.last_obj = None
        self.reset()
        self.uuid = str(uuid4())
        self.state = Running(None)
        self.full = False
        self.below = False
        self.connect()

    def run_file(self, filename):
        """Run the file `filename` with trace"""
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
        """Run the cmd `cmd` with trace"""
        if globals is None:
            import __main__
            globals = __main__.__dict__
        if locals is None:
            locals = globals
        self.reset()
        if isinstance(cmd, str):
            cmd = compile(cmd, "<string>", "exec")
        self.start_trace()
        self.breakpoints.add(Breakpoint(fn, temporary=True))
        try:
            execute(cmd, globals, locals)
        finally:
            self.stop_trace()

    def reset(self):
        """Refresh linecache"""
        import linecache
        linecache.checkcache()

    def connect(self):
        """Connect to wdb server"""
        log.info('Connecting socket on %s:%d' % (SOCKET_SERVER, SOCKET_PORT))
        self._socket = Client((SOCKET_SERVER, SOCKET_PORT))
        Wdb._sockets.append(self._socket)
        self._socket.send_bytes(self.uuid.encode('utf-8'))

    def trace_dispatch(self, frame, event, arg):
        """This function is called every line,
        function call, function return and exception during trace"""
        fun = getattr(self, 'handle_' + event)
        if fun and (
                (
                    event is 'line' and self.breaks(frame)
                ) or (
                    event is 'exception' and (
                        self.full or frame == self.state.frame or (
                            self.below and frame.f_back == self.state.frame
                        )
                    )
                ) or self.state.stops(frame, event)):
            fun(frame, arg)

        if event is 'return' and frame == self.state.frame:
            # Upping state
            if self.state.up():
                # No more frames
                self.stop_trace()
                return
            # Threading / Multiprocessing support
            co = self.state.frame.f_code
            if ((
                    co.co_filename.endswith('threading.py') and
                    co.co_name.endswith('_bootstrap_inner')
            ) or (self.state.frame.f_code.co_filename.endswith(
                os.path.join('multiprocessing', 'process.py')) and
                    self.state.frame.f_code.co_name == '_bootstrap')):
                # Thread / Process is dead
                self.stop_trace()
                self.die()
                return
        if (event is 'call' and not self.stepping and not self.full and
                not (self.below and frame.f_back == self.state.frame) and
                not self.get_file_breaks(frame.f_code.co_filename)):
            # Don't trace anymore here
            trace_log.debug("Don't trace %s" % pretty_frame(frame))
            return
        return self.trace_dispatch

    def trace_debug_dispatch(self, frame, event, arg):
        """Utility function to add debug to tracing"""
        trace_log.info('Frame:%s. Event: %s. Arg: %r' % (
            pretty_frame(frame), event, arg))
        trace_log.debug('state %r breaks ? %s stops ? %s' % (
            self.state,
            self.breaks(frame, no_remove=True),
            self.state.stops(frame, event)
        ))
        if event is 'return':
            trace_log.debug(
                'Return: frame: %s, state: %s, state.f_back: %s' % (
                    pretty_frame(frame), pretty_frame(self.state.frame),
                    pretty_frame(self.state.frame.f_back)))
        if self.trace_dispatch(frame, event, arg):
            return self.trace_debug_dispatch

    def start_trace(self, full=False, frame=None, below=False):
        """Start tracing from here"""
        if self.tracing:
            return
        self.reset()
        log.info('Starting trace on %r' % self.thread)
        frame = frame or sys._getframe().f_back
        # Setting trace without pausing
        self.set_trace(frame, break_=False)
        self.tracing = True
        self.below = below
        self.full = full

    def set_trace(self, frame=None, break_=True):
        """Break at current state"""
        # We are already tracing, do nothing
        if self.stepping:
            return
        self.reset()
        trace = (self.trace_dispatch
                 if trace_log.level >= 30 else self.trace_debug_dispatch)
        trace_frame = frame = frame or sys._getframe().f_back
        while frame:
            frame.f_trace = trace
            frame = frame.f_back
        self.state = Step(trace_frame) if break_ else Running(trace_frame)
        sys.settrace(trace)

    def stop_trace(self, frame=None):
        """Stop tracing from here"""
        self.tracing = False
        self.full = False
        frame = frame or sys._getframe().f_back
        while frame:
            del frame.f_trace
            frame = frame.f_back
        sys.settrace(None)
        log.info('Stopping trace on %r' % self.thread)

    def set_until(self, frame, lineno=None):
        """Stop on the next line number."""
        self.state = Until(frame, frame.f_lineno)

    def set_step(self, frame):
        """Stop on the next line."""
        self.state = Step(frame)

    def set_next(self, frame):
        """Stop on the next line in current frame."""
        self.state = Next(frame)

    def set_return(self, frame):
        """Stop when returning from the given frame."""
        self.state = Return(frame)

    def set_continue(self, frame):
        """Don't stop anymore"""
        self.state = Running(frame)
        if not self.tracing and not self.breakpoints:
            # If we were in a set_trace and there's no breakpoint to trace for
            # Run without trace
            self.stop_trace()

    def set_break(self, filename, lineno=None, temporary=False, cond=None,
                  funcname=None):
        """Put a breakpoint for filename"""
        log.info('Setting break fn:%s lno:%s tmp:%s cond:%s fun:%s' % (
            filename, lineno, temporary, cond, funcname))
        if lineno:
            if cond:
                breakpoint = ConditionalBreakpoint(
                    filename, lineno, cond, temporary)
            else:
                breakpoint = LineBreakpoint(filename, lineno, temporary)
        elif funcname:
            breakpoint = FunctionBreakpoint(filename, funcname, temporary)
        else:
            breakpoint = Breakpoint(filename, temporary)
        self.breakpoints.add(breakpoint)
        log.info('Breakpoint %r added' % breakpoint)

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
            self.hooked += self.safe_better_repr(obj) + '\n'
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
        import linecache
        return ''.join(linecache.getlines(filename))

    def get_stack(self, f, t):
        """Build the stack from frame and traceback"""
        stack = []
        if t and t.tb_frame is f:
            t = t.tb_next
        while f is not None:
            stack.append((f, f.f_lineno))
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
        import linecache
        frames = []
        stack, _ = self.get_stack(frame, tb)
        current = 0

        for i, (stack_frame, lno) in enumerate(stack):
            if frame == stack_frame:
                current = i
                break

        for i, (stack_frame, lno) in enumerate(stack):
            code = stack_frame.f_code
            filename = code.co_filename
            if filename == '<wdb>' and w_code:
                line = w_code
            else:
                linecache.checkcache(filename)
                line = linecache.getline(filename, lno, stack_frame.f_globals)
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
                'level': i,
                'current': current == i
            })

        # While in exception always put the context to the top
        current = len(frames) - 1

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
            web_url = 'http://%s:%d/debug/session/%s' % (
                WEB_SERVER or 'localhost',
                WEB_PORT or 1984,
                self.uuid)

            server = WEB_SERVER or '[wdb.server]'
            if WEB_PORT:
                server += ':%s' % WEB_PORT

            if WDB_NO_BROWSER_AUTO_OPEN:
                log.warn('You can now launch your browser at '
                         'http://%s/debug/session/%s' % (
                             server,
                             self.uuid))

            elif not webbrowser.open(web_url):
                log.warn('Unable to open browser, '
                         'please go to http://%s/debug/session/%s' % (
                             server,
                             self.uuid))

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

    def handle_call(self, frame, argument_list):
        """This method is called when there is the remote possibility
        that we ever need to stop in this function."""
        fun = frame.f_code.co_name
        log.info('Calling: %r' % fun)
        init = 'Echo|%s' % dump({
            'for': '__call__',
            'val': fun})
        self.interaction(
            frame, init=init,
            exception_description='Calling %s' % fun)

    def handle_line(self, frame, arg):
        """This function is called when we stop or break at this line."""
        log.info('Stopping at line %s' % pretty_frame(frame))
        self.interaction(frame)

    def handle_return(self, frame, return_value):
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

    def handle_exception(self, frame, exc_info):
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
        log.warn(pretty_frame(frame))
        frame = frame or sys._getframe().f_back.f_back.f_back.f_back
        self.interaction(
            frame, tb, exception, exception_description, init=init)

    def breaks(self, frame, no_remove=False):
        """Return True if there's a breakpoint at frame"""
        for breakpoint in set(self.breakpoints):
            if breakpoint.breaks(frame):
                if breakpoint.temporary and not no_remove:
                    self.breakpoints.remove(breakpoint)
                return True
        return False

    def get_file_breaks(self, filename):
        """List all file `filename` breakpoints"""
        return [breakpoint for breakpoint in self.breakpoints
                if breakpoint.on_file(filename)]

    def get_breaks_lno(self, filename):
        """List all line numbers that have a breakpoint"""
        return list(
            filter(lambda x: x is not None,
                   [getattr(breakpoint, 'line', None)
                    for breakpoint in self.breakpoints
                    if breakpoint.on_file(filename)]))

    def clear_break(self, filename, line):
        """Remove a breakpoint"""
        for breakpoint in set(self.breakpoints):
            if getattr(breakpoint, 'line', None):
                if breakpoint.line == line:
                    self.breakpoints.remove(breakpoint)

    def die(self):
        """Time to quit"""
        log.info('Time to die')
        try:
            self.send('Die')
        except:
            pass
        self._socket.close()
        self.pop()


def set_trace(frame=None):
    """Set trace on current line, or on given frame"""
    frame = frame or sys._getframe().f_back
    wdb = Wdb.get()
    wdb.set_trace(frame)


def start_trace(full=False, frame=None, below=False):
    """Start tracing program at callee level
       breaking on exception/breakpoints"""
    wdb = Wdb.get()
    if not wdb.stepping:
        wdb.start_trace(full, frame or sys._getframe().f_back, below)


def stop_trace(frame=None, close_on_exit=False):
    """Start tracing program at callee level
       breaking on exception/breakpoints"""
    log.info('Stopping trace?')
    wdb = Wdb.get(True)  # Do not create an istance if there's None
    if wdb and (not wdb.stepping or close_on_exit):
        log.info('Stopping trace')
        wdb.stop_trace(frame or sys._getframe().f_back)
        if close_on_exit:
            wdb.die()


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
    """Close all sockets at exit"""
    for socket in Wdb._sockets:
        socket.close()
