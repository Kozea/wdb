# *-* coding: utf-8 *-*
# This file is part of wdb
#
# wdb Copyright (C) 2012-2014  Florian Mounier, Kozea
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
from __future__ import with_statement
__version__ = '2.1.3'
_initial_globals = dict(globals())

from ._compat import (
    execute, StringIO, to_unicode_string, escape, loads, Socket)

from .breakpoint import (
    Breakpoint, LineBreakpoint,
    ConditionalBreakpoint, FunctionBreakpoint)

from collections import defaultdict
from .ui import Interaction, dump
from .utils import pretty_frame, executable_line, get_args
from .state import Running, Step, Next, Until, Return
from contextlib import contextmanager
from log_colorizer import get_color_logger
from uuid import uuid4
import dis
import os
import logging
import sys
import threading
import socket
import webbrowser
import atexit
import time

# Get wdb server host
SOCKET_SERVER = os.getenv('WDB_SOCKET_SERVER', 'localhost')
# and port
SOCKET_PORT = int(os.getenv('WDB_SOCKET_PORT', '19840'))

# Get wdb web server host
WEB_SERVER = os.getenv('WDB_WEB_SERVER')
# and port
WEB_PORT = int(os.getenv('WDB_WEB_PORT', 0))

WDB_NO_BROWSER_AUTO_OPEN = bool(os.getenv('WDB_NO_BROWSER_AUTO_OPEN', False))

log = get_color_logger('wdb')
trace_log = logging.getLogger('wdb.trace')

for log_name in ('main', 'trace', 'ui', 'ext', 'bp'):
    logger = 'wdb.%s' % log_name if log_name != 'main' else 'wdb'
    level = os.getenv(
        'WDB_%s_LOG' % log_name.upper(),
        os.getenv('WDB_LOG', 'WARNING')).upper()
    logging.getLogger(logger).setLevel(getattr(logging, level, 'WARNING'))


class Wdb(object):
    """Wdb debugger main class"""
    _instances = {}
    _sockets = []
    enabled = True
    breakpoints = set()
    watchers = defaultdict(set)

    @staticmethod
    def get(no_create=False, server=SOCKET_SERVER, port=SOCKET_PORT):
        """Get the thread local singleton"""
        pid = os.getpid()
        thread = threading.current_thread()
        wdb = Wdb._instances.get((pid, thread))
        if not wdb and not no_create:
            wdb = object.__new__(Wdb)
            Wdb.__init__(wdb, server, port)
            wdb.pid = pid
            wdb.thread = thread
            Wdb._instances[(pid, thread)] = wdb
        else:
            if wdb and (wdb.server != server or wdb.port != port):
                log.warn('Different server/port set, ignoring')
        return wdb

    @staticmethod
    def pop():
        """Remove instance from instance list"""
        pid = os.getpid()
        thread = threading.current_thread()
        Wdb._instances.pop((pid, thread))

    def __new__(cls, server=SOCKET_SERVER, port=SOCKET_PORT):
        return cls.get(server=server, port=port)

    def __init__(self, server=SOCKET_SERVER, port=SOCKET_PORT):
        log.debug('New wdb instance %r' % self)
        self.obj_cache = {}
        self.compile_cache = {}
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
        self.below = 0
        self.under = None
        self.server = server
        self.port = port
        self._socket = None
        self.connect()
        self.get_breakpoints()

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
            statement = compile(fp.read(), filename, 'exec')
        self.run(statement, filename)

    def run(self, cmd, fn=None, globals=None, locals=None):
        """Run the cmd `cmd` with trace"""
        if globals is None:
            import __main__
            globals = __main__.__dict__
        if locals is None:
            locals = globals
        self.reset()
        if isinstance(cmd, str):
            str_cmd = cmd
            cmd = compile(str_cmd, fn or "<wdb>", "exec")
            self.compile_cache[id(cmd)] = str_cmd
        if fn:
            from linecache import getline
            lno = 1
            while True:
                line = getline(fn, lno, globals)
                if line is None:
                    lno = None
                    break
                if executable_line(line):
                    break
                lno += 1

        self.start_trace()
        if lno is not None:
            self.breakpoints.add(LineBreakpoint(fn, lno, temporary=True))
        try:
            execute(cmd, globals, locals)
        finally:
            self.stop_trace()

    def reset(self):
        """Refresh linecache"""
        import linecache
        linecache.checkcache()

    def reconnect_if_needed(self):
        try:
            # Sending PING twice
            self.send('PING')
            self.send('PING')
            log.debug('Dual ping sent')
        except BrokenPipeError:
            log.warning('BrokenPipe on ping, connection lost retrying')
            self._socket = None
            self.connected = False
            self.begun = False
            self.connect()

    def connect(self):
        """Connect to wdb server"""
        log.info('Connecting socket on %s:%d' % (self.server, self.port))
        tries = 0
        while not self._socket and tries < 10:
            try:
                time.sleep(.2 * tries)
                self._socket = Socket((self.server, self.port))
            except socket.error:
                tries += 1
                log.warning(
                    'You must start/install wdb.server '
                    '(Retrying on %s:%d) [Try #%d/10]' % (
                        self.server, self.port, tries))
                self._socket = None

        if not self._socket:
            log.error('Could not connect to server')
            sys.exit(2)

        Wdb._sockets.append(self._socket)
        self._socket.send_bytes(self.uuid.encode('utf-8'))

    def get_breakpoints(self):
        log.info('Getting server breakpoints')
        self.send('ServerBreaks')
        breaks = self.receive()
        breaks = loads(breaks)
        self._init_breakpoints = breaks

        for brk in breaks:
            self.set_break(
                brk['fn'], brk['lno'], False,
                brk['cond'], brk['fun'])

        log.info('Server breakpoints added')

    def breakpoints_to_json(self):
        return [brk.to_dict() for brk in self.breakpoints]

    def check_below(self, frame):
        stop_frame = self.state.frame

        if not self.below and not self.under:
            return frame == stop_frame, False

        if self.under:
            stop_frame = None
            iframe = frame
            while iframe is not None:
                if iframe.f_code == self.under.__code__:
                    stop_frame = iframe
                iframe = iframe.f_back
        iframe = frame
        if not stop_frame:
            return False, False
        below = 0
        while iframe is not None:
            if stop_frame == iframe:
                break
            below += 1
            iframe = iframe.f_back

        return below == self.below, below == self.below

    def trace_dispatch(self, frame, event, arg):
        """This function is called every line,
        function call, function return and exception during trace"""
        fun = getattr(self, 'handle_' + event, None)
        if not fun:
            return self.trace_dispatch
        below, continue_below = self.check_below(frame)
        if (self.state.stops(frame, event) or
            (event == 'line' and self.breaks(frame)) or
                (event == 'exception' and (self.full or below))):
            fun(frame, arg)
        if event == 'return' and frame == self.state.frame:
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

        if (event == 'call' and not self.stepping and not self.full and
                not continue_below and
                not self.get_file_breaks(frame.f_code.co_filename)):
            # Don't trace anymore here
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
        if event == 'return':
            trace_log.debug(
                'Return: frame: %s, state: %s, state.f_back: %s' % (
                    pretty_frame(frame), pretty_frame(self.state.frame),
                    pretty_frame(self.state.frame.f_back)))
        if self.trace_dispatch(frame, event, arg):
            return self.trace_debug_dispatch
        trace_log.debug("No trace %s" % pretty_frame(frame))

    def start_trace(self, full=False, frame=None, below=0, under=None):
        """Start tracing from here"""
        if self.tracing:
            return
        self.reset()
        log.info('Starting trace')
        frame = frame or sys._getframe().f_back
        # Setting trace without pausing
        self.set_trace(frame, break_=False)
        self.tracing = True
        self.below = below
        self.under = under
        self.full = full

    def set_trace(self, frame=None, break_=True):
        """Break at current state"""
        # We are already tracing, do nothing
        trace_log.info('Setting trace %s (stepping %s) (current_trace: %s)' % (
            pretty_frame(frame or sys._getframe().f_back), self.stepping,
            sys.gettrace()))
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
        log.info('Stopping trace')

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

    def get_break(self, filename, lineno, temporary, cond, funcname):
        if lineno and not cond:
            return LineBreakpoint(filename, lineno, temporary)
        elif cond:
            return ConditionalBreakpoint(
                filename, lineno, cond, temporary)
        elif funcname:
            return FunctionBreakpoint(filename, funcname, temporary)
        else:
            return Breakpoint(filename, temporary)

    def set_break(self, filename, lineno=None, temporary=False, cond=None,
                  funcname=None):
        """Put a breakpoint for filename"""
        log.info('Setting break fn:%s lno:%s tmp:%s cond:%s fun:%s' % (
            filename, lineno, temporary, cond, funcname))
        breakpoint = self.get_break(
            filename, lineno, temporary, cond, funcname)
        self.breakpoints.add(breakpoint)
        log.info('Breakpoint %r added' % breakpoint)
        return breakpoint

    def clear_break(self, filename, lineno=None, temporary=False, cond=None,
                    funcname=None):
        """Remove a breakpoint"""
        log.info('Removing break fn:%s lno:%s tmp:%s cond:%s fun:%s' % (
            filename, lineno, temporary, cond, funcname))

        breakpoint = self.get_break(
            filename, lineno, temporary or False, cond, funcname)
        if temporary is None and breakpoint not in self.breakpoints:
            breakpoint = self.get_break(
                filename, lineno, True, cond, funcname)

        try:
            self.breakpoints.remove(breakpoint)
            log.info('Breakpoint %r removed' % breakpoint)
        except Exception:
            log.info('Breakpoint %r not removed: not found' % breakpoint)

    def safe_repr(self, obj):
        """Like a repr but without exception"""
        try:
            return repr(obj)
        except Exception as e:
            return '??? Broken repr (%s: %s)' % (type(e).__name__, e)

    def safe_better_repr(self, obj, context=None, html=True, level=0):
        """Repr with inspect links on objects"""
        context = context and dict(context) or {}
        recursion = id(obj) in context
        if not recursion:
            context[id(obj)] = obj
            try:
                rv = self.better_repr(obj, context, html, level + 1)
            except Exception:
                rv = None
            if rv:
                return rv

        self.obj_cache[id(obj)] = obj
        if html:
            return '<a href="%d" class="inspect">%s%s</a>' % (
                id(obj),
                'Recursion of ' if recursion else '',
                escape(self.safe_repr(obj)))
        return '%s%s' % (
            'Recursion of ' if recursion else '',
            self.safe_repr(obj))

    def better_repr(self, obj, context=None, html=True, level=1):
        """Repr with html decorations or indentation"""
        if isinstance(obj, dict):
            dict_repr = '  ' * (level - 1)
            if type(obj) != dict:
                dict_repr = type(obj).__name__ + '({'
                closer = '})'
            else:
                dict_repr = '{'
                closer = '}'
            if len(obj) > 2:
                dict_repr += '\n' + '  ' * level
                if html:
                    dict_repr += '<table>'
                    dict_repr += ''.join([
                        '<tr><td>' + self.safe_repr(key) + '</td><td>:</td>'
                        '<td>' + self.safe_better_repr(
                            val, context, html, level) +
                        '</td></tr>'
                        for key, val in sorted(
                            obj.items(),
                            key=lambda x: x[0])])
                    dict_repr += '</table>'
                else:
                    dict_repr += ('\n' + '  ' * level).join([
                        self.safe_repr(key) + ': ' + self.safe_better_repr(
                            val, context, html, level)
                        for key, val in sorted(
                            obj.items(),
                            key=lambda x: x[0])])
                closer = '\n' + '  ' * (level - 1) + closer
            else:
                dict_repr += ', '.join([
                    self.safe_repr(key) + ': ' + self.safe_better_repr(
                        val, context, html, level)
                    for key, val in sorted(obj.items(), key=lambda x: x[0])])
            dict_repr += closer
            return dict_repr

        if any([
                isinstance(obj, list),
                isinstance(obj, set),
                isinstance(obj, tuple)]):
            iter_repr = '  ' * (level - 1)
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
                splitter += '\n' + '  ' * level
                iter_repr += '\n' + '  ' * level
                closer = '\n' + '  ' * (level - 1) + closer

            iter_repr += splitter.join(
                [self.safe_better_repr(
                    val, context, html, level)
                 for val in obj])

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
        import linecache
        # Hack for frozen importlib bootstrap
        if filename == '<frozen importlib._bootstrap>':
            filename = os.path.join(os.path.dirname(linecache.__file__),
                                    'importlib', '_bootstrap.py')
        return to_unicode_string(
            ''.join(linecache.getlines(filename)), filename)

    def get_stack(self, f, t):
        """Build the stack from frame and traceback"""
        stack = []
        if t and t.tb_frame == f:
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

    def get_trace(self, frame, tb):
        """Get a dict of the traceback for wdb.js use"""
        import linecache
        frames = []
        stack, _ = self.get_stack(frame, tb)
        current = 0

        for i, (stack_frame, lno) in enumerate(stack):
            code = stack_frame.f_code
            filename = code.co_filename
            linecache.checkcache(filename)
            line = linecache.getline(filename, lno, stack_frame.f_globals)
            if not line:
                line = self.compile_cache.get(id(code), '')
            line = to_unicode_string(line, filename)
            line = line and line.strip()
            startlnos = dis.findlinestarts(code)
            lastlineno = list(startlnos)[-1][1]
            if frame == stack_frame:
                current = i
            frames.append({
                'file': filename,
                'function': code.co_name,
                'flno': code.co_firstlineno,
                'llno': lastlineno,
                'lno': lno,
                'code': line,
                'level': i,
                'current': frame == stack_frame
            })

        # While in exception always put the context to the top
        return stack, frames, current

    def send(self, data):
        """Send data through websocket"""
        log.debug('Sending %s' % data)
        self._socket.send_bytes(data.encode('utf-8'))

    def receive(self):
        """Receive data through websocket"""
        log.debug('Receiving')
        try:
            data = self._socket.recv_bytes()
        except EOFError:
            log.error('Connection lost')
            sys.exit(1)
        log.debug('Got %s' % data)
        return data.decode('utf-8')

    def open_browser(self):
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
                log.warning('You can now launch your browser at '
                            'http://%s/debug/session/%s' % (
                                server,
                                self.uuid))

            elif not webbrowser.open(web_url):
                log.warning('Unable to open browser, '
                            'please go to http://%s/debug/session/%s' % (
                                server,
                                self.uuid))

            self.connected = True

    def shell(self, source=None, vars=None):
        interaction = self.interaction(
            sys._getframe(), exception_description='Shell',
            shell=True, shell_vars=vars)

        if source:
            with open(source) as f:
                compiled_code = compile(f.read(), '<source>', 'exec')
            # Executing in locals to keep local scope
            # (http://bugs.python.org/issue16781)
            execute(
                compiled_code,
                interaction.current_locals,
                interaction.current_locals)

        interaction.loop()

    def interaction(
            self, frame, tb=None,
            exception='Wdb', exception_description='Stepping',
            init=None, shell=False, shell_vars=None):
        """User interaction handling blocking on socket receive"""
        log.info('Interaction %r %r %r %r' % (
            frame, tb, exception, exception_description))
        self.reconnect_if_needed()
        self.stepping = True

        self.open_browser()

        interaction = Interaction(
            self, frame, tb, exception, exception_description,
            init=init, shell=shell, shell_vars=shell_vars)

        # For meta debugging purpose
        self._ui = interaction

        if self.begun:
            # Each new state sends the trace and selects a frame
            interaction.init()
        else:
            self.begun = True
        if not shell:
            interaction.loop()

        return interaction

    def handle_call(self, frame, argument_list):
        """This method is called when there is the remote possibility
        that we ever need to stop in this function."""
        fun = frame.f_code.co_name
        log.info('Calling: %r' % fun)

        init = 'Echo|%s' % dump({
            'for': '__call__',
            'val': '%s(%s)' % (fun, get_args(frame))})
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
            'val': self.safe_repr(return_value)
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

    def die(self):
        """Time to quit"""
        log.info('Time to die')
        if self.connected:
            try:
                self.send('Die')
            except Exception:
                pass
            self._socket.close()
        self.pop()


def set_trace(frame=None, skip=0, server=SOCKET_SERVER, port=SOCKET_PORT):
    """Set trace on current line, or on given frame"""
    frame = frame or sys._getframe().f_back
    for i in range(skip):
        if not frame.f_back:
            break
        frame = frame.f_back
    wdb = Wdb.get()
    wdb.set_trace(frame)
    return wdb


def start_trace(full=False, frame=None, below=0, under=None,
                server=SOCKET_SERVER, port=SOCKET_PORT):
    """Start tracing program at callee level
       breaking on exception/breakpoints"""
    wdb = Wdb.get(server=server, port=port)
    if not wdb.stepping:
        wdb.start_trace(full, frame or sys._getframe().f_back, below, under)
    return wdb


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
    return wdb


class trace(object):
    def __init__(self, **kwargs):
        """Make a tracing context with `with trace():`"""
        self.kwargs = kwargs

    def __enter__(self):
        #  2 calls to get here
        kwargs = dict(self.kwargs)
        if 'close_on_exit' in kwargs:
            kwargs.pop('close_on_exit')
        kwargs.setdefault('frame', sys._getframe().f_back)
        start_trace(**kwargs)

    def __exit__(self, *args):
        kwargs = {}
        kwargs['frame'] = self.kwargs.get('frame', sys._getframe().f_back)
        kwargs['close_on_exit'] = self.kwargs.get('close_on_exit', False)
        stop_trace(**kwargs)


@atexit.register
def cleanup():
    """Close all sockets at exit"""
    for sck in Wdb._sockets:
        sck.close()


def shell(source=None, vars=None):
    """Start a shell sourcing source or using vars as locals"""
    Wdb.get().shell(source=source, vars=vars)


# Pdb compatibility

def post_mortem(t=None, server=SOCKET_SERVER, port=SOCKET_PORT):
    if t is None:
        t = sys.exc_info()[2]
        if t is None:
            raise ValueError(
                "A valid traceback must be passed if no "
                "exception is being handled")

    wdb = Wdb.get(server=server, port=port)
    wdb.reset()
    wdb.interaction(None, t)


def pm(server=SOCKET_SERVER, port=SOCKET_PORT):
    post_mortem(sys.last_traceback, server=server, port=port)
