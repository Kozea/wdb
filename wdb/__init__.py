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

# from _bdbdb import Bdb, BdbQuit  # Bdb with lot of log
from bdb import Bdb, BdbQuit
import pdb
import traceback
from cgi import escape
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
from hashlib import sha512
try:
    from urlparse import parse_qs
except ImportError:
    def parse_qs(qs):
        return dict([x.split("=") for x in qs.split("&")])
from pprint import pprint, pformat
from gc import get_objects
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO  import StringIO
import os
import sys
import re
import dis

RES_PATH = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), 'resources')

REPR = re.compile(escape(r'<?\S+\s(object|instance)\sat\s([0-9a-fx]+)>?'))
log = get_color_logger('wdb')
log.setLevel(30)


def reverse_id(id_):
    for obj in get_objects():
        if id(obj) == id_:
            return obj


@contextmanager
def capture_output():
    stdout, stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = StringIO(), StringIO()
    out, err = [], []
    try:
        yield out, err
    finally:
        out.extend(sys.stdout.getvalue().splitlines())
        err.extend(sys.stderr.getvalue().splitlines())
        sys.stdout, sys.stderr = stdout, stderr


class ReprEncoder(JSONEncoder):
    def default(self, obj):
        print obj
        return repr(obj)


def dump(o):
    out = dumps(o, cls=ReprEncoder, sort_keys=True)

    def repr_handle(match):
        repr_ = match.group(0)
        try:
            id_ = int(match.group(2), 16)
        except:
            id_ = None

        return (
            '<a href="%d" class="inspect">%s</a>' % (id_, repr_)
        ).replace('"', '\\"')

    return REPR.sub(repr_handle, out)


class WdbOff(Exception):
    pass


class MetaWdbRequest(type):
    def __init__(cls, name, bases, dict):
        MetaWdbRequest.started = False
        try:
            from werkzeug.serving import ThreadedWSGIServer
            ThreadedWSGIServer.daemon_threads = True
        except ImportError:
            pass
        super(MetaWdbRequest, cls).__init__(name, bases, dict)
        cls._last_inst = None

    def __call__(cls, *args, **kwargs):
        cls._last_inst = super(MetaWdbRequest, cls).__call__(*args, **kwargs)
        return cls._last_inst

    def tf(cls, frame=None):
        self = cls._last_inst
        log.info('Setting trace')
        if not self:
            if MetaWdbRequest.started:
                raise WdbOff()
            else:
                log.warn("[Wdb] We are outside of request, "
                         "launching pdb.set_trace instead")
                pdb.set_trace(frame or sys._getframe().f_back)
                return
        sys.settrace(None)
        fframe = frame = frame or sys._getframe().f_back
        while frame and frame is not self.botframe:
            del frame.f_trace
            frame = frame.f_back
        self.set_trace(fframe)


class Wdb(object):

    @property
    def html(self):
        with open(os.path.join(RES_PATH, 'wdb.html')) as f:
            return f.read()

    @property
    def _500(self):
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
            self.enabled = path.endswith('on')
            start_response('200 OK', [('Content-Type', 'text/html')])
            return ('<h1>Wdb is now %s</h1>' % (
                '<span style="color: green">ON</span>' if self.enabled else
                '<span style="color: red">OFF</span>'),)
        elif path.startswith('/__wdb/'):
            filename = path.replace('/__wdb/', '')
            log.debug('Getting static "%s"' % filename)
            return self.static_request(
                environ, start_response, filename)
        elif ((self.enabled or path == '/__wdb') and
              'text/html' in environ.get('HTTP_ACCEPT', '')):
            log.debug('Sending fake page (%s) for %s' % (
                environ['HTTP_ACCEPT'], path))
            return self.first_request(environ, start_response)
        elif environ.get('HTTP_X_DEBUGGER', '').startswith('WDB'):
            port = int(environ['HTTP_X_DEBUGGER'].split('-')[1])
            log.debug('Sending real page (%s) with exception'
                      ' handling for %s' % (
                          environ.get('HTTP_ACCEPT', ''), path))
            app = self.app
            if path == '/__wdb':
                def set_trace(environ, start_response):
                    start_response('200 OK', [('Content-Type', 'text/html')])
                    WdbRequest.tf()
                    yield "Done"
                app = set_trace
            return WdbRequest(port).wsgi_trace(
                app, environ, start_response)
        else:
            log.debug("Serving %s" % path)

            def wsgi_default(environ, start_response):
                appiter = None
                try:
                    appiter = self.app(environ, start_response)
                    for item in appiter:
                        yield item
                    hasattr(appiter, 'close') and appiter.close()
                except WdbOff:
                    hasattr(appiter, 'close') and appiter.close()
                    try:
                        start_response('500 INTERNAL SERVER ERROR', [
                            ('Content-Type', 'text/html')])
                        yield self._500 % dict(
                            message='Wdb.set_trace() was called '
                            'while wdb was off.',
                            trace='')
                    except:
                        pass
                except:
                    log.exception('Exception with wdb off')
                    hasattr(appiter, 'close') and appiter.close()
                    try:
                        start_response('500 INTERNAL SERVER ERROR', [
                            ('Content-Type', 'text/html')])
                        yield self._500 % dict(
                            message='There was an exception in your '
                            'request and wdb was off.',
                            trace=traceback.format_exc())
                    except:
                        pass

            return wsgi_default(environ, start_response)

    def static_request(self, environ, start_response, filename):
        start_response('200 OK', [('Content-Type', guess_type(filename)[0])])
        with open(os.path.join(RES_PATH, filename)) as f:
            yield f.read()

    def first_request(self, environ, start_response):
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

        yield self.html % dict(post=post, theme=self.theme)


class WdbRequest(object, Bdb):
    """Wdb debugger main class"""
    __metaclass__ = MetaWdbRequest

    def __init__(self, port, skip=None):
        try:
            Bdb.__init__(self, skip=skip)
        except TypeError:
            Bdb.__init__(self)
        self.begun = False
        self.connected = False
        self.make_web_socket(port)

    def make_web_socket(self, port):
        log.info('Creating WebSocket')
        self.ws = WebSocket('0.0.0.0', port)

    def wsgi_trace(self, app, environ, start_response):
        def wsgi_with_trace(environ, start_response):
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

    def get_file(self, filename, html_escape=True):
        checkcache(filename)
        file_ = ''.join(getlines(filename))
        if not html_escape:
            return file_
        return escape(file_)

    def handle_connection(self):
        if self.connected:
            try:
                self.send('Ping')
            except:
                log.exception('Ping Failed')
                self.connected = False
        tries = 0
        while not self.connected and tries < 10:
            tries += 1
            try:
                self.ws.wait_for_connect()
            except WsError:
                log.exception('Unable to connect')
            else:
                self.connected = True

    def get_trace(self, frame, tb, w_code=None):
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
                'code': escape(line),
                'level': i
            })

        return stack, frames, current

    def interaction(
            self, frame, tb=None,
            exception='Wdb', exception_description='Set Trace'):
        if not self.ws:
            raise BdbQuit()
        try:
            self._interaction(
                frame, tb, exception, exception_description)
        except WsError:
            log.exception('Websocket Error during interaction. Starting again')
            self.handle_connection()
            self.interaction(
                frame, tb, exception, exception_description)

    def send(self, data):
        self.ws.send(data)

    def receive(self):
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
        log.debug('Interaction for %r %r %r %r' % (
            frame, tb, exception, exception_description))
        stack, trace, current_index = self.get_trace(frame, tb)
        current = trace[current_index]
        locals = stack[current_index][0].f_locals
        if self.begun:
            self.send('Trace|%s' % dump({
                'trace': trace,
                'cwd': os.getcwd()
            }))
            current_file = current['file']
            self.send('Check|%s' % dump({
                'name': current_file,
                'sha512': sha512(self.get_file(current_file)).hexdigest()
            }))
        else:
            self.begun = True

        while True:
            message = self.receive()
            if '|' in message:
                pipe = message.index('|')
                cmd = message[:pipe]
                data = message[pipe + 1:]
            else:
                cmd = message
                data = ''

            log.debug('Cmd %s #Data %d' % (cmd, len(data)))
            if cmd == 'Start':
                self.send('Title|%s' % dump({
                    'title': exception,
                    'subtitle': exception_description
                }))
                self.send('Trace|%s' % dump({
                    'trace': trace,
                    'cwd': os.getcwd()
                }))
                current_file = current['file']
                self.send('Check|%s' % dump({
                    'name': current_file,
                    'sha512': sha512(self.get_file(current_file)).hexdigest()
                }))

            elif cmd == 'Select':
                current_index = int(data)
                current = trace[current_index]
                current_file = current['file']
                self.send('Check|%s' % dump({
                    'name': current_file,
                    'sha512': sha512(self.get_file(current_file)).hexdigest()
                }))

            elif cmd == 'File':
                current_file = current['file']
                self.send('Select|%s' % dump({
                    'frame': current,
                    'breaks': self.get_file_breaks(current_file),
                    'file': self.get_file(current_file),
                    'name': current_file,
                    'sha512': sha512(self.get_file(current_file)).hexdigest()
                }))

            elif cmd == 'NoFile':
                self.send('Select|%s' % dump({
                    'frame': current,
                    'breaks': self.get_file_breaks(current['file'])
                }))

            elif cmd == 'Inspect':
                thing = reverse_id(int(data))
                self.send('Dump|%s' % dump({
                    'for': escape(repr(thing)),
                    'val': escape(pformat(dict(
                        (key, getattr(thing, key))
                        for key in dir(thing))))
                }))

            elif cmd == 'Trace':
                self.send('Trace|%s' % dump({
                    'trace': trace,
                    'cwd': os.getcwd()
                }))

            elif cmd == 'Eval':
                globals = dict(stack[current_index][0].f_globals)
                # Hack for function scope eval
                globals.update(locals)
                globals.setdefault('pprint', pprint)
                with capture_output() as (out, err):
                    try:
                        compiled_code = compile(data, '<stdin>', 'single')
                        exec compiled_code in globals, locals
                    except Exception:
                        type_, value, tb = exc_info()
                        print '%s: %s' % (type_.__name__, str(value))
                self.send('Print|%s' % dump({
                    'result': escape('\n'.join(out) + '\n'.join(err))
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
                if ':' in data:
                    fn, lno = data.split(':')
                else:
                    fn, lno = current['file'], data
                cond = None
                if ',' in lno:
                    lno, cond = lno.split(',')
                    cond = cond.lstrip()

                lno = int(lno)
                rv = self.set_break(fn, lno, int(cmd == 'TBreak'), cond)
                log.info('Break set at %s:%d [%s]' % (fn, lno, rv))
                if rv is None:
                    if fn == current['file']:
                        self.send('BreakSet|%s' % dump({
                            'lno': lno, 'cond': cond
                        }))
                    else:
                        self.send('BreakSet|%s' % dump({}))
                else:
                    self.send('Log|%s' % dump({
                        'message': rv
                    }))

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
                    log.error('Jump failed')
                    continue

                trace[current_index]['lno'] = lno
                self.send('Trace|%s' % dump({
                    'trace': trace,
                    'cwd': os.getcwd()
                }))
                self.send('Select|%s' % dump({
                    'frame': current,
                    'breaks': self.get_file_breaks(current['file'])
                }))

            elif cmd == 'Complete':
                current_file = current['file']
                file_ = self.get_file(current_file, False).decode('utf-8')
                lines = file_.split(u'\n')
                lno = trace[current_index]['lno']
                line_before = lines[lno - 1]
                indent = len(line_before) - len(line_before.lstrip())
                segments = data.split(u'\n')
                for segment in reversed(segments):
                    line = u' ' * indent + segment
                    lines.insert(lno - 1, line)
                try:
                    completions = Script(
                        u'\n'.join(lines), lno - 1 + len(segments),
                        len(segments[-1]) + indent, current_file).complete()
                except:
                    self.send('Log|%s' % dump({
                        'message': 'Completion failed for %s' %
                        '\n'.join(reversed(segments))
                    }))
                else:
                    self.send('Suggest|%s' % dump({
                        'completions': [{
                            'base': comp.word[
                                :len(comp.word) - len(comp.complete)],
                            'complete': comp.complete,
                            'description': comp.description
                        } for comp in completions if comp.word.endswith(
                            comp.complete)]
                    }))

            elif cmd == 'Quit':
                if hasattr(self, 'botframe'):
                    self.set_continue()
                    raise BdbQuit()
                break

            else:
                log.warn('Unknown command %s' % cmd)

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
        log.info('Stopping at line %r:%d' % (
            frame.f_code.co_filename, frame.f_lineno))
        self.handle_connection()
        log.debug('User Line Interaction for %r' % frame)
        self.interaction(frame)

    def user_return(self, frame, return_value):
        """This function is called when a return trap is set here."""
        frame.f_locals['__return__'] = return_value
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
        log.error('Exception', exc_info=exc_info)
        type_, value, tb = exc_info
        frame.f_locals['__exception__'] = type_, value
        exception = type_.__name__
        exception_description = str(value)
        self.handle_connection()
        self.send('Echo|%s' % dump({
            'for': '__exception__',
            'val': '%s: %s' % (
            exception, exception_description)}))
        if not self.begun:
            frame = None
        self.interaction(frame, tb, exception, exception_description)

    def do_clear(self, arg):
        log.info('Closing %r' % arg)
        self.clear_bpbynumber(arg)

    def dispatch_exception(self, frame, arg):
        self.user_exception(frame, arg)
        if self.quitting:
            raise BdbQuit
        return self.trace_dispatch


def set_trace(frame=None):
    WdbRequest.tf(frame or sys._getframe().f_back)
