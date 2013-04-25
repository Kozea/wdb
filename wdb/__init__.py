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

# from _bdbdb import Bdb, BdbQuit, Breakpoint  # Bdb with lot of log
from bdb import Bdb, BdbQuit, Breakpoint
import traceback
from cgi import escape
from tempfile import gettempdir
from shutil import move
try:
    from json import dumps, JSONEncoder
except ImportError:
    from simplejson import dumps, JSONEncoder

from contextlib import contextmanager
from linecache import checkcache, getlines, getline
from log_colorizer import get_color_logger
from jedi import Script
from sys import exc_info
from websocket import WebSocket, WsError
from mimetypes import guess_type
from random import randint
try:
    from urlparse import parse_qs
except ImportError:
    def parse_qs(qs):
        return dict([x.split("=") for x in qs.split("&")])

from urllib import quote
from multiprocessing import active_children, Process
from signal import SIGKILL
import atexit

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO  import StringIO
import os
import sys
import time
import dis

BASE_PATH = os.path.join(
    os.path.abspath(os.path.dirname(__file__)))
RES_PATH = os.path.join(BASE_PATH, 'resources')

log = get_color_logger('wdb')
log.setLevel(30)


class ReprEncoder(JSONEncoder):
    """JSON encoder using repr for objects"""

    def default(self, obj):
        return repr(obj)


def dump(o):
    """Shortcut to json.dumps with ReprEncoder"""
    return dumps(o, cls=ReprEncoder, sort_keys=True)


class WdbOff(Exception):
    """Wdb is disabled"""
    pass


class AltServer(Process):
    """Process spawning a wsgi server to serve wdb when used outside wsgi"""

    def __init__(self, ports, *args, **kwargs):
        log.debug('Starting alt server with ports %s' % ports)
        self.ports = ports
        super(AltServer, self).__init__(*args, **kwargs)
        self.daemon = 1
        self.start()

    def run(self):
        """Run the process"""
        from wsgiref.simple_server import (
            make_server, WSGIServer, WSGIRequestHandler)
        from SocketServer import ThreadingMixIn

        class ThreadingServer(ThreadingMixIn, WSGIServer):
            """Threaded wsgi"""

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
                with open(os.path.join(BASE_PATH, filename)) as f:
                    return f.read(),

            # Serving wdb page
            log.debug('Getting wdb page from fork')
            start_response('200 OK', [('Content-Type', 'text/html')])
            with open(os.path.join(RES_PATH, 'wdb.html')) as f:
                return f.read() % dict(
                    post='false', theme='dark', alt_ports=self.ports),

        httpd = make_server(
            '', 2001, trace_app,
            server_class=ThreadingServer, handler_class=SilentHandler)

        # Monkey patch httpserver to launch webbrowser.open just in time
        from BaseHTTPServer import HTTPServer
        old_serve_forever = HTTPServer.serve_forever

        def new_serve_forever(self):
            import webbrowser
            webbrowser.open('http://localhost:2001/')
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
        MetaWdbRequest._last_inst = None

    def tf(cls, frame=None):
        """Set trace in frame or in current frame"""
        log.info('Setting trace')

        # Get the last request which must be the current
        wdbr = MetaWdbRequest._last_inst
        if not wdbr:
            # If there's none:

            if MetaWdbRequest.started:
                # But Wdb was init: wdb is disabled
                raise WdbOff()
            else:
                # Wdb was not init: we are outside any WSGI Request
                log.warn(
                    'Wdb set_trace was called outside of a wsgi application. '
                    'Debugger is now running at http://localhost:2001/.')

                # Spawn a server to inspect code throught wdb
                wdbr = Wdb.make_server()

        # Removing current global tracing function if any
        sys.settrace(None)
        frame = frame or sys._getframe().f_back
        top_frame = frame
        # Remove local tracing functions if any
        while frame and frame is not wdbr.botframe:
            del frame.f_trace
            frame = frame.f_back

        # Set trace to the top frame
        wdbr.set_trace(top_frame)


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
                MetaWdbRequest._last_inst = None
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
                            title=type(e).__name__,
                            subtitle=str(e),
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
        rand_ports = [randint(10000, 60000) for _ in range(5)]
        AltServer(rand_ports)
        wdbr = WdbRequest(rand_ports)
        wdbr.quitting = 0
        wdbr.begun = False
        wdbr.reset()
        return wdbr


class WdbRequest(object, Bdb):
    """Wdb debugger main class"""
    __metaclass__ = MetaWdbRequest

    def __init__(self, ports, skip=None):
        MetaWdbRequest._last_inst = self
        self.obj_cache = {}

        try:
            Bdb.__init__(self, skip=skip)
        except TypeError:
            Bdb.__init__(self)
        self.begun = False
        self.connected = False
        self.make_web_socket(ports)
        self.extra_vars = {}
        self.last_obj = None
        breaks_per_file_lno = Breakpoint.bplist.values()
        for bps in breaks_per_file_lno:
            breaks = list(bps)
            for bp in breaks:
                args = bp.file, bp.line, bp.temporary, bp.cond
                self.set_break(*args)
                log.info('Resetting break %s' % repr(args))

        atexit.register(lambda: self.die())

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

    def make_web_socket(self, ports):
        """Create a web socket"""

        log.info('Creating WebSocket')
        for port in ports:
            self.ws = WebSocket('0.0.0.0', port)
            if self.ws.status == 'OK':
                return
            time.sleep(.100)

        raise WsError('No port could be opened')

    def wsgi_trace(self, app, environ, start_response):
        """WSGI with a tracing function activated"""

        def wsgi_with_trace(environ, start_response):
            """Inner WSGI gen"""
            self.quitting = 0
            self.begun = False
            self.reset()
            frame = sys._getframe()
            while frame:
                frame.f_trace = self.trace_dispatch
                self.botframe = frame
                frame = frame.f_back
            self.stopframe = sys._getframe().f_back
            self.stoplineno = -1
            sys.settrace(self.trace_dispatch)

            try:
                appiter = app(environ, start_response)
            except BdbQuit:
                sys.settrace(None)
                start_response('200 OK', [('Content-Type', 'text/html')])
                yield '<h1>BdbQuit</h1><p>Wdb was interrupted</p>'
            else:
                for item in appiter:
                    yield item
                hasattr(appiter, 'close') and appiter.close()
                sys.settrace(None)
                self.ws.force_close()
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

    def handle_exc(self):
        """Return a formated exception traceback for wdb.js use"""
        type_, value = exc_info()[:2]
        return '<a title="%s">%s: %s</a>' % (
            escape(traceback.format_exc().replace('"', '\'')),
            escape(type_.__name__), escape(str(value)))

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
        self.ws.send(data)

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
        stack, trace, current_index = self.get_trace(frame, tb)
        current = trace[current_index]
        # Copy locals to avoid strange cpython behaviour
        locals_ = map(lambda x: x[0].f_locals, stack)

        def get_globals():
            """Get enriched globals"""
            globals_ = dict(stack[current_index][0].f_globals)
            globals_['_'] = self.last_obj
            # Hack for function scope eval
            globals_.update(locals_[current_index])
            for var, val in self.extra_vars.items():
                globals_[var] = val
            self.extra_items = {}
            return globals_

        if self.begun:
            # Each new state sends the trace and selects a frame
            self.send('Trace|%s' % dump({
                'trace': trace,
                'cwd': os.getcwd()
            }))
            current_file = current['file']
            self.send('Select|%s' % dump({
                'frame': current,
                'breaks': self.get_file_breaks(current_file),
                'file': self.get_file(current_file),
                'name': current_file
            }))
        else:
            self.begun = True

        while True:
            try:
                try:
                    message = self.receive()
                except KeyboardInterrupt:
                    # Quit on KeyboardInterrupt
                    message = 'Quit'

                # Parse received message
                if '|' in message:
                    pipe = message.index('|')
                    cmd = message[:pipe]
                    data = message[pipe + 1:]
                else:
                    cmd = message
                    data = ''

                def fail(title=None, message=None):
                    """Send back captured exceptions"""
                    if message is None:
                        message = self.handle_exc()
                    else:
                        message = escape(message)
                    self.send('Echo|%s' % dump({
                        'for': escape(title or '%s failed' % cmd),
                        'val': message
                    }))

                log.debug('Cmd %s #Data %d' % (cmd, len(data)))
                if cmd == 'Start':
                    self.send('Init|%s' % dump({
                        'cwd': os.getcwd()
                    }))
                    self.send('Title|%s' % dump({
                        'title': exception,
                        'subtitle': exception_description
                    }))
                    self.send('Trace|%s' % dump({
                        'trace': trace
                    }))
                    current_file = current['file']
                    self.send('Select|%s' % dump({
                        'frame': current,
                        'breaks': self.get_file_breaks(current_file),
                        'file': self.get_file(current_file),
                        'name': current_file
                    }))

                elif cmd == 'Select':
                    current_index = int(data)
                    current = trace[current_index]
                    current_file = current['file']
                    self.send('Select|%s' % dump({
                        'frame': current,
                        'breaks': self.get_file_breaks(current_file),
                        'file': self.get_file(current_file),
                        'name': current_file
                    }))

                elif cmd == 'Inspect':
                    try:
                        thing = self.obj_cache.get(int(data))
                    except Exception:
                        fail()
                        continue
                    self.send('Dump|%s' % dump({
                        'for': repr(thing),
                        'val': self.dmp(thing)}))

                elif cmd == 'Dump':
                    try:
                        thing = eval(
                            data, get_globals(), locals_[current_index])
                    except Exception:
                        fail()
                        continue
                    else:
                        self.send('Dump|%s' % dump({
                            'for': u'%s ⟶ %s ' % (data, repr(thing)),
                            'val': self.dmp(thing)}))

                elif cmd == 'Trace':
                    self.send('Trace|%s' % dump({
                        'trace': trace
                    }))

                elif cmd == 'Eval':
                    redir = None
                    raw_data = data = data.strip()
                    if '!>' in data:
                        data, redir = data.split('!>')
                        data = data.strip()
                        redir = redir.strip()
                    elif data.startswith('!<'):
                        filename = data[2:].strip()
                        try:
                            with open(filename, 'r') as f:
                                data = f.read()
                        except Exception:
                            fail('Unable to read from file %s' % filename)
                            continue

                    with self.capture_output(
                            with_hook=redir is None) as (out, err):
                        try:
                            compiled_code = compile(data, '<stdin>', 'single')
                            l = locals_[current_index]
                            exec compiled_code in get_globals(), l
                        except Exception:
                            self.hooked = self.handle_exc()
                    if redir:
                        try:
                            with open(redir, 'w') as f:
                                f.write('\n'.join(out) + '\n'.join(err) + '\n')
                        except Exception:
                            fail('Unable to write to file %s' % redir)
                            continue
                        self.send('Print|%s' % dump({
                            'for': raw_data,
                            'result': escape('Written to file %s' % redir)
                        }))
                    else:
                        self.send('Print|%s' % dump({
                            'for': raw_data,
                            'result': self.hooked + escape(
                                '\n'.join(out) + '\n'.join(err))
                        }))

                elif cmd == 'Ping':
                    self.send('Pong')

                elif cmd == 'Step':
                    if hasattr(self, 'botframe'):
                        self.set_step()
                    break

                elif cmd == 'Next':
                    if hasattr(self, 'botframe'):
                        self.set_next(stack[current_index][0])
                    break

                elif cmd == 'Continue':
                    if hasattr(self, 'botframe'):
                        self.set_continue()
                    break

                elif cmd == 'Return':
                    if hasattr(self, 'botframe'):
                        self.set_return(stack[current_index][0])
                    break

                elif cmd == 'Until':
                    if hasattr(self, 'botframe'):
                        self.set_until(stack[current_index][0])
                    break

                elif cmd in ('TBreak', 'Break'):
                    break_fail = lambda x: fail(
                        'Break on %s failed' % data, message=x)
                    if ':' in data:
                        fn, lno = data.split(':')
                    else:
                        fn, lno = current['file'], data
                    cond = None
                    if ',' in lno:
                        lno, cond = lno.split(',')
                        cond = cond.lstrip()

                    try:
                        lno = int(lno)
                    except:
                        break_fail(
                            'Wrong breakpoint format must be '
                            '[file:]lno[,cond].')
                        continue

                    line = getline(
                        fn, lno, stack[current_index][0].f_globals)
                    if not line:
                        break_fail('Line does not exist')
                        continue
                    line = line.strip()
                    if ((not line or (line[0] == '#') or
                         (line[:3] == '"""') or
                         line[:3] == "'''")):
                        break_fail('Blank line or comment')
                        continue

                    first_rv = rv = self.set_break(
                        fn, lno, int(cmd == 'TBreak'), cond)
                    if rv is not None:
                        for path in sys.path:
                            rv = self.set_break(
                                os.path.join(path, fn),
                                lno, int(cmd == 'TBreak'), cond)
                            if rv is None:
                                break
                    if rv is None:
                        log.info('Break set at %s:%d [%s]' % (fn, lno, rv))
                        if fn == current['file']:
                            self.send('BreakSet|%s' % dump({
                                'lno': lno, 'cond': cond
                            }))
                        else:
                            self.send('BreakSet|%s' % dump({}))
                    else:
                        break_fail(first_rv)

                elif cmd == 'Unbreak':
                    lno = int(data)
                    current_file = current['file']
                    log.info('Break unset at %s:%d' % (current_file, lno))
                    self.clear_break(current_file, lno)
                    self.send('BreakUnset|%s' % dump({'lno': lno}))

                elif cmd == 'Jump':
                    lno = int(data)
                    if current_index != len(trace) - 1:
                        log.error('Must be at bottom frame')
                        continue

                    try:
                        stack[current_index][0].f_lineno = lno
                    except ValueError:
                        fail()
                        continue

                    trace[current_index]['lno'] = lno
                    self.send('Trace|%s' % dump({
                        'trace': trace
                    }))
                    self.send('Select|%s' % dump({
                        'frame': current,
                        'breaks': self.get_file_breaks(current['file'])
                    }))

                elif cmd == 'Complete':
                    current_file = current['file']
                    file_ = self.get_file(current_file).decode('utf-8')
                    lines = file_.split(u'\n')
                    lno = trace[current_index]['lno']
                    line_before = lines[lno - 1]
                    indent = len(line_before) - len(line_before.lstrip())
                    segments = data.split(u'\n')
                    for segment in reversed(segments):
                        line = u' ' * indent + segment
                        lines.insert(lno - 1, line)
                    script = Script(
                        u'\n'.join(lines), lno - 1 + len(segments),
                        len(segments[-1]) + indent, '')
                    try:
                        completions = script.complete()
                    except:
                        log.exception('Completion failed')
                        self.send('Log|%s' % dump({
                            'message': 'Completion failed for %s' %
                            '\n'.join(reversed(segments))
                        }))
                    else:
                        fun = script.get_in_function_call()
                        self.send('Suggest|%s' % dump({
                            'params': {
                                'params': [p.get_code().replace('\n', '')
                                           for p in fun.params],
                                'index': fun.index,
                                'module': fun.module.path,
                                'call_name': fun.call_name} if fun else None,
                            'completions': [{
                                'base': comp.word[
                                    :len(comp.word) - len(comp.complete)],
                                'complete': comp.complete,
                                'description': comp.description
                            } for comp in completions if comp.word.endswith(
                                comp.complete)]
                        }))

                elif cmd == 'Save':
                    pipe = data.index('|')
                    fn = data[:pipe]
                    src = data[pipe + 1:]
                    if os.path.exists(fn):
                        dn = os.path.dirname(fn)
                        bn = os.path.basename(fn)
                        try:
                            move(
                                fn, os.path.join(
                                    gettempdir(),
                                    dn.replace(os.path.sep, '!') + bn +
                                    '-wdb-back-%d' % time.time()))
                            with open(fn, 'w') as f:
                                f.write(src.encode('utf-8'))
                        except OSError as e:
                            self.send('Echo|%s' % dump({
                                'for': 'Error during save',
                                'val': str(e)
                            }))
                        else:
                            self.send('Echo|%s' % dump({
                                'for': 'Save succesful',
                                'val': 'Wrote %s' % fn
                            }))

                elif cmd == 'Quit':
                    if hasattr(self, 'botframe'):
                        self.set_continue()
                        raise BdbQuit()
                    break

                else:
                    log.warn('Unknown command %s' % cmd)

            except BdbQuit:
                # This will be handled by caller
                raise
            except Exception:
                try:
                    exc = self.handle_exc()
                    type_, value = exc_info()[:2]
                    link = ('<a href="https://github.com/Kozea/wdb/issues/new?'
                            'title=%s&body=%s&labels=defect" class="nogood">'
                            'Please click here to report it on Github</a>') % (
                                quote('%s: %s' % (type_.__name__, str(value))),
                                quote('```\n%s\n```\n' %
                                      traceback.format_exc()))
                    self.send('Echo|%s' % dump({
                        'for': 'Error in Wdb, this is bad',
                        'val': exc + '<br>' + link
                    }))
                except:
                    self.send('Echo|%s' % dump({
                        'for': 'Too many errors',
                        'val': ("Don't really know what to say. "
                                "Maybe it will work tomorrow.")
                    }))
                    continue

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
        log.debug('EXC')
        log.error('Exception', exc_info=exc_info)
        type_, value, tb = exc_info
        # exc = type_, value
        self.obj_cache[id(exc_info)] = exc_info
        self.extra_vars['__exception__'] = exc_info
        exception = type_.__name__
        exception_description = str(value)
        self.handle_connection()
        self.send('Echo|%s' % dump({
            'for': '__exception__',
            'val': escape('%s: %s') % (
                exception, exception_description)}))
        if not self.begun:
            frame = None
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
        self.send('Die')


def set_trace(frame=None):
    """Set trace on current line, or on given frame"""
    WdbRequest.tf(frame or sys._getframe().f_back)
