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
from .websocket import WebSocket, WsError, WsBroken
from io import StringIO
from bdb import BdbQuit, Breakpoint
from cgi import escape
from contextlib import contextmanager
from linecache import checkcache, getlines, getline
from log_colorizer import get_color_logger
from mimetypes import guess_type
from multiprocessing import Process
from random import randint, seed
import atexit
import dis
import os
import sys
import threading
import time
import traceback

BASE_PATH = os.path.join(
    os.path.abspath(os.path.dirname(__file__)))
RES_PATH = os.path.join(BASE_PATH, 'resources')

log = get_color_logger('wdb')
log.setLevel(30)


class WdbOff(Exception):
    """Wdb is disabled"""
    pass


class AltServer(Process):
    """Process spawning a wsgi server to serve wdb when used outside wsgi"""

    def __init__(self, http_port, ws_ports, *args, **kwargs):
        self.ws_ports = ws_ports
        self.http_port = http_port
        super(AltServer, self).__init__(*args, **kwargs)
        self.daemon = 1

    def run(self):
        """Run the process"""
        log.debug('Starting alt server on port %d with ports %s' % (
            self.http_port, self.ws_ports))
        from wsgiref.simple_server import (
            make_server, WSGIServer, WSGIRequestHandler)
        from ._compat import ThreadingMixIn

        class ThreadingServer(ThreadingMixIn, WSGIServer):
            """Threaded wsgi"""
            daemon_threads = True

            def process_request(self, request, client_address):
                """Override thread start with no_trace on"""
                t = threading.Thread(target=self.process_request_thread,
                                     args=(request, client_address))
                t.daemon = self.daemon_threads
                t.no_trace = True
                t.start()

        class SilentHandler(WSGIRequestHandler):
            """Silent handler"""

            def log_message(self, f, *args):
                return

        def trace_app(environ, start_response):
            """Served wsgi app"""
            path = environ.get('PATH_INFO', '')
            # Serving statics
            if path.startswith('/__wdb/'):
                filename = path.replace('/__wdb/', '')
                log.debug('Getting static "%s"' % filename)
                start_response(
                    '200 OK', [('Content-Type', guess_type(filename)[0])])
                with open(os.path.join(BASE_PATH, filename), 'rb') as f:
                    return f.read(),

            # Serving wdb page
            log.debug('Getting wdb page from fork')
            start_response('200 OK', [('Content-Type', 'text/html')])
            with open(os.path.join(RES_PATH, 'wdb.html'), 'r') as f:
                return to_bytes(f.read() % dict(
                    post='false', theme='dark', alt_ports=self.ws_ports)),
        port = self.http_port
        started = False

        while not started and port < 60001:
            try:
                httpd = make_server(
                    '', port, trace_app,
                    server_class=ThreadingServer, handler_class=SilentHandler)
            except:
                port += 1000
            else:
                started = True

        # Monkey patch httpserver to launch webbrowser.open just in time
        from ._compat import HTTPServer
        old_serve_forever = HTTPServer.serve_forever

        def new_serve_forever(self):
            import webbrowser
            webbrowser.open('http://localhost:%d/' % port)
            old_serve_forever(self)
        HTTPServer.serve_forever = new_serve_forever

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


class MetaWdbRequest(type):
    """Metaclass of Wdbrequest"""

    def __init__(cls, name, bases, dict):
        MetaWdbRequest.started = False
        try:
            from werkzeug.serving import ThreadedWSGIServer
            ThreadedWSGIServer.daemon_threads = True
        except ImportError:
            pass
        super(MetaWdbRequest, cls).__init__(name, bases, dict)
        MetaWdbRequest._instances = {}

    def tf(cls, frame=None):
        """Set trace in frame or in current frame"""
        log.info('Setting trace')
        # Removing current global tracing function if any
        sys.settrace(None)

        # Get the last request which must be the current
        wdbr = MetaWdbRequest._instances.get(threading.current_thread())
        if not wdbr:
            # If there's none:

            if MetaWdbRequest.started:
                # But Wdb was init: wdb is disabled
                raise WdbOff()
            else:
                # Wdb was not init: we are outside any WSGI Request
                log.warn(
                    'Wdb set_trace was called outside of a wsgi application.')

                # Spawn a server to inspect code throught wdb
                wdbr = Wdb.make_server()

        frame = frame or sys._getframe().f_back
        # Clear previous tracing
        wdbr.stop_trace()
        # Set trace to the top frame
        wdbr.set_trace(frame)


class Wdb(object):

    @property
    def html(self):
        """Property used to return the wdb page"""
        with open(os.path.join(RES_PATH, 'wdb.html')) as f:
            return f.read()

    @property
    def _500(self):
        """Property used to return the wdb error page"""
        with open(os.path.join(RES_PATH, '500.html')) as f:
            return f.read()

    def __init__(self, app, start_disabled=False, theme='dark'):
        self.app = app
        self.theme = theme
        self.enabled = not start_disabled
        MetaWdbRequest.started = True

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')

        if path in ('/__wdb/on', '/__wdb/off'):
            # Enable / Disable wdb
            self.enabled = path.endswith('on')
            if not self.enabled:
                for thread in threading.enumerate():
                    MetaWdbRequest._instances[thread] = None
            start_response('200 OK', [('Content-Type', 'text/html')])
            return self._500 % dict(
                trace_dict={}, trace='',
                title='Switched ' + ('ON' if self.enabled else 'OFF'),
                subtitle='You can now go back to your normal pages',
                theme=self.theme,
                state=('de' if self.enabled else ''))

        elif path.startswith('/__wdb/'):
            # Serve static files
            filename = path.replace('/__wdb/', '')
            log.debug('Getting static "%s"' % filename)
            return self.static_request(
                environ, start_response, filename)

        elif ((self.enabled or path == '/__wdb') and
              'text/html' in environ.get('HTTP_ACCEPT', '')):
            # Send page that will get the real page back in ajax
            log.debug('Sending fake page (%s) for %s' % (
                environ['HTTP_ACCEPT'], path))
            return self.first_request(environ, start_response)

        elif environ.get('HTTP_X_DEBUGGER', '').startswith('WDB'):
            # Send page that will get the real page back in ajax
            ports = map(
                int, environ['HTTP_X_DEBUGGER'].split('-')[1].split(','))
            log.debug('Sending real page (%s) with tracing function on'
                      ' for %s' % (
                          environ.get('HTTP_ACCEPT', ''), path))
            app = self.app
            if path == '/__wdb':
                # Set trace on url /__wdb
                def set_trace(environ, start_response):
                    start_response('200 OK', [('Content-Type', 'text/html')])
                    WdbRequest.tf()
                    yield "Done"
                app = set_trace
            return WdbRequest(ports).wsgi_trace(app, environ, start_response)
        else:
            log.debug("Serving %s" % path)
            # Serving normally with exception handling

            def wsgi_default(environ, start_response):
                appiter = None
                try:
                    appiter = self.app(environ, start_response)
                    for item in appiter:
                        yield item
                    hasattr(appiter, 'close') and appiter.close()
                except WdbOff:
                    hasattr(appiter, 'close') and appiter.close()
                    tb = sys.exc_info()[2]
                    stack = traceback.extract_tb(tb)
                    stack.reverse()
                    try:
                        start_response('500 INTERNAL SERVER ERROR', [
                            ('Content-Type', 'text/html')])
                        yield self._500 % dict(
                            theme=self.theme,
                            trace='',
                            state='',
                            title='Wdb',
                            subtitle='Set Trace (Please set Wdb On)',
                            trace_dict=dump({'trace': stack[2:]}))
                    except:
                        log.exception('Uh oh')

                except Exception as e:
                    log.exception('Exception with wdb off')
                    hasattr(appiter, 'close') and appiter.close()
                    tb = sys.exc_info()[2]
                    stack = traceback.extract_tb(tb)
                    stack.reverse()
                    try:
                        start_response('500 INTERNAL SERVER ERROR', [
                            ('Content-Type', 'text/html')])
                        yield self._500 % dict(
                            theme=self.theme,
                            trace=traceback.format_exc(),
                            title=type(e).__name__.replace("'", "\\'"),
                            subtitle=str(e).replace("'", "\\'"),
                            state='',
                            trace_dict=dump({
                                'trace': stack,
                            })
                        )
                    except:
                        log.exception('Uh oh')

            return wsgi_default(environ, start_response)

    def static_request(self, environ, start_response, filename):
        """Return static file"""
        start_response('200 OK', [('Content-Type', guess_type(filename)[0])])
        with open(os.path.join(BASE_PATH, filename)) as f:
            yield f.read()

    def first_request(self, environ, start_response):
        """Return page that will call real request in ajax"""
        post = 'null'
        if environ.get('REQUEST_METHOD', '') == 'POST':
            post = {}
            body = ''
            try:
                length = int(environ.get('CONTENT_LENGTH', '0'))
            except ValueError:
                pass
            else:
                body = environ['wsgi.input'].read(length)
            post['enctype'] = environ.get('CONTENT_TYPE', '')
            if not 'multipart/form-data' in post['enctype']:
                post['data'] = parse_qs(body)
            else:
                post['data'] = body
            post = dump(post)
        start_response('200 OK', [('Content-Type', 'text/html')])
        log.info('Starting new request')

        yield self.html % dict(post=post, theme=self.theme, alt_ports='null')

    @staticmethod
    def make_server():
        """Make a wsgi server and start a WdbRequest"""
        seed()
        rand_ports = [randint(10000, 60000) for _ in range(5)]
        wdbr = WdbRequest(rand_ports)
        wdbr.reset()
        wdbr.server = AltServer(
            2520 + threading.enumerate().index(threading.current_thread()),
            rand_ports)
        return wdbr

    @staticmethod
    def trace(full=False):
        """Make an instance of Wdb and trace all code below"""
        wdbr = MetaWdbRequest._instances.get(threading.current_thread())
        if not wdbr:
            log.info('Tracing with a new server')
            # Let's make a server
            wdbr = Wdb.make_server()
        else:
            sys.settrace(None)
            log.info('Tracing with an existing server')
            wdbr.reset()
            wdbr.stop_trace()
            wdbr.begun = False

        def trace(frame, event, arg):
            rv = wdbr.trace_dispatch(frame, event, arg)
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
        wdbr.stoplineno = -1
        wdbr.stopframe = frame
        while frame:
            frame.f_trace = trace
            wdbr.botframe = frame
            frame = frame.f_back

        # Set trace with wdb
        sys.settrace(trace)
        return wdbr

    @staticmethod
    def run_file(filename):
        import __main__
        __main__.__dict__.clear()
        __main__.__dict__.update({
            "__name__": "__main__",
            "__file__": filename,
            "__builtins__": __builtins__,
        })
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


class WdbRequest(Bdb, with_metaclass(MetaWdbRequest)):
    """Wdb debugger main class"""

    def __init__(self, ports, skip=None):
        MetaWdbRequest._instances[threading.current_thread()] = self
        self.obj_cache = {}

        try:
            Bdb.__init__(self, skip=skip)
        except TypeError:
            Bdb.__init__(self)
        self.begun = False
        self.quitting = False
        self.connected = False
        self.ports = ports
        self.extra_vars = {}
        self.last_obj = None
        self.server_started = False
        self.server = None
        self.reset()
        breaks_per_file_lno = Breakpoint.bplist.values()
        for bps in breaks_per_file_lno:
            breaks = list(bps)
            for bp in breaks:
                args = bp.file, bp.line, bp.temporary, bp.cond
                self.set_break(*args)
                log.info('Resetting break %s' % repr(args))

        atexit.register(lambda: self.die())

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

    @property
    def ws(self):
        if not self.server_started:
            self.server_started = True
            if self.server is not None:
                if hasattr(os, '_original_fork'):
                    os._fork = os.fork
                    os.fork = os._original_fork
                    self.server.start()
                    os.fork = os._fork
                else:
                    self.server.start()

            self.make_web_socket(self.ports)
        return self.__ws

    def make_web_socket(self, ports):
        """Create a web socket"""

        log.info('Creating WebSocket %r' % self)
        for port in ports:
            self.__ws = WebSocket('0.0.0.0', port)
            if self.ws.status == 'OK':
                return
            time.sleep(.100)

        raise WsError('No port could be opened')

    def wsgi_trace(self, app, environ, start_response):
        """WSGI with a tracing function activated"""

        def wsgi_with_trace(environ, start_response):
            """Inner WSGI gen"""
            Wdb.trace()

            try:
                appiter = app(environ, start_response)
            except BdbQuit:
                self.stop_trace()
                start_response('200 OK', [('Content-Type', 'text/html')])
                yield '<h1>BdbQuit</h1><p>Wdb was interrupted</p>'
            else:
                for item in appiter:
                    yield item
                hasattr(appiter, 'close') and appiter.close()
                self.stop_trace()
                self.die()
        return wsgi_with_trace(environ, start_response)

    def get_file(self, filename):
        """Get file source from cache"""
        checkcache(filename)
        return ''.join(getlines(filename))

    def handle_connection(self):
        """Check connection state, and try to reconnect if it's broken"""
        if self.connected:
            try:
                self.send('Ping')
            except:
                log.exception('Ping Failed')
                self.connected = False
        if not self.connected:
            self.ws.wait_for_connect()
            self.connected = True

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

    def interaction(
            self, frame, tb=None,
            exception='Wdb', exception_description='Set Trace'):
        """Entry point of user interaction"""
        if not self.ws:
            raise BdbQuit()
        try:
            self._interaction(
                frame, tb, exception, exception_description)
        except WsError:
            log.exception('Websocket Error during interaction. Starting again')
            self.handle_connection()
            # Recursive call to restart interaction on ws crash
            self.interaction(
                frame, tb, exception, exception_description)

    def send(self, data):
        """Send data through websocket"""
        try:
            self.ws.send(data)
        except WsBroken:
            if self.server:
                import webbrowser
                webbrowser.open('http://localhost:%d/' % self.server.http_port)
                self.ws.wait_for_connect()
            else:
                raise

    def receive(self):
        """Receive data through websocket"""
        message = None
        while not message:
            rv = self.ws.receive()
            if rv == 'CLOSED':
                raise WsError
            message = rv
        return message

    def _interaction(
            self, frame, tb,
            exception, exception_description):
        """User interaction handling blocking on socket receive"""

        log.debug('Interaction for %r %r %r %r' % (
            frame, tb, exception, exception_description))

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
            self.handle_connection()
            self.send('Echo|%s' % dump({
                'for': '__call__',
                'val': fun}))
            self.interaction(frame)

    def user_line(self, frame):
        """This function is called when we stop or break at this line."""
        log.debug('LINE')
        log.info('Stopping at line %r:%d' % (
            frame.f_code.co_filename, frame.f_lineno))
        self.handle_connection()
        log.debug('User Line Interaction for %r' % frame)
        self.interaction(frame)

    def user_return(self, frame, return_value):
        """This function is called when a return trap is set here."""
        self.obj_cache[id(return_value)] = return_value
        self.extra_vars['__return__'] = return_value
        log.info('Returning from %r with value: %r' % (
            frame.f_code.co_name, return_value))
        self.handle_connection()
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
        self.handle_connection()
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

    def die(self):
        """That's the end my friend"""
        if self.server_started and self.begun:
            log.info('Dying')
            self.send('Die')


def set_trace(frame=None):
    """Set trace on current line, or on given frame"""
    WdbRequest.tf(frame or sys._getframe().f_back)
