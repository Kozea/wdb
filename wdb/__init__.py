# *-* coding: utf-8 *-*
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

from bdb import Bdb
from cgi import escape
from json import dumps, JSONEncoder
from contextlib import contextmanager
from linecache import checkcache, getlines, getline
from log_colorizer import get_color_logger
from random import randint
from sys import exc_info
from websocket import WebSocket, WsError
from mimetypes import guess_type
from hashlib import sha512
from urlparse import parse_qs
from pprint import pprint, pformat
from gc import get_objects
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO  import StringIO
import os
import sys
import re

RES_PATH = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), 'resources')

REPR = re.compile(escape(r'<?\S+\s(object|instance)\sat\s([0-9a-fx]+)>?'))

log = get_color_logger('wdb')
# log.setLevel(20)


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


class MetaWdb(type):

    def __init__(cls, name, bases, dict):
        super(MetaWdb, cls).__init__(name, bases, dict)
        cls._inst_ = None

    def __call__(cls, *args, **kwargs):
        if cls._inst_:
            raise NotImplementedError(
                'One debugger is allowed at a time, '
                '%r already registered' % cls._inst_)

        cls._inst_ = super(MetaWdb, cls).__call__(*args, **kwargs)
        return cls._inst_

    def tf(cls, frame=None):
        log.info('Setting trace')
        if not cls._inst_:
            raise Exception("Can't set trace outside of request")
        cls._inst_.begun = False
        cls._inst_.set_trace(frame or sys._getframe().f_back)


class Wdb(object, Bdb):
    """Wdb debugger main class"""
    __metaclass__ = MetaWdb

    @property
    def html(self):
        with open(os.path.join(RES_PATH, 'wdb.html')) as f:
            return f.read()

    def __init__(self, app, skip=None):
        Bdb.__init__(self, skip=skip)
        self.begun = False
        self.app = app
        self.ws = WebSocket('localhost', randint(10000, 60000))
        self.connected = False
        tries = 1
        while self.ws == 'FAIL' and tries < 10:
            tries += 1
            self.ws = WebSocket('localhost', randint(10000, 60000))

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        if path.startswith('/__wdb/'):
            filename = path.replace('/__wdb/', '')
            log.debug('Getting static "%s"' % filename)
            return self.static_request(
                environ, start_response, filename)
        elif 'text/html' in environ.get('HTTP_ACCEPT', ''):
            log.debug('Sending fake page (%s) for %s' % (
                environ['HTTP_ACCEPT'], path))
            return self.first_request(environ, start_response)
        else:
            log.debug('Sending real page (%s) for %s' % (
                environ.get('HTTP_ACCEPT', ''), path))
            return self.handled_request(environ, start_response)

    def static_request(self, environ, start_response, filename):
        start_response('200 OK', [('Content-Type', guess_type(filename)[0])])
        with open(os.path.join(RES_PATH, filename)) as f:
            yield f.read()

    def handled_request(self, environ, start_response):
        self.quitting = 0
        appiter = None
        try:
            appiter = self.app(environ, start_response)
            for item in appiter:
                yield item
            if hasattr(appiter, 'close'):
                appiter.close()
        except Exception:
            log.exception('wdb')
            if hasattr(appiter, 'close'):
                appiter.close()

            self.handle_connection()
            type_, value, tb = exc_info()
            exception = type_.__name__
            exception_description = str(value)
            self.interaction(None, tb, exception, exception_description)
            try:
                start_response('500 INTERNAL SERVER ERROR', [
                    ('Content-Type', 'text/html')])
                yield (
                    '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">'
                    '<title>500 Internal Server Error</title>'
                    '<h1>Internal Server Error</h1>'
                    '<p>There was an error in your request.</p>')
            except:
                pass

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
        yield self.html.format(port=self.ws.port, post=post)

    def get_file(self, filename):
        checkcache(filename)
        return escape(''.join(getlines(filename)))

    # WDB
    def handle_connection(self):
        if self.connected:
            ret = None
            try:
                self.ws.send('Ping')
                ret = self.ws.receive()
            except:
                log.exception('Ping Failed')
            self.connected = ret == 'Pong'

        if not self.connected:
            self.ws.wait_for_connect()
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

            frames.append({
                'file': filename,
                'function': code.co_name,
                'flno': code.co_firstlineno,
                'lno': lno,
                'code': escape(line),
                'level': i
            })

        return stack, frames, current

    def interaction(
            self, frame, tb=None,
            exception='Wdb', exception_description='Set Trace'):
        try:
            self._interaction(
                frame, tb, exception, exception_description)
        except WsError:
            log.exception('Websocket Error during interaction. Starting again')
            self.handle_connection()
            self.interaction(
                frame, tb, exception, exception_description)

    def _interaction(
            self, frame, tb,
            exception, exception_description):
        stack, trace, current_index = self.get_trace(frame, tb)
        current = trace[current_index]
        locals = stack[current_index][0].f_locals
        if self.begun:
            self.ws.send('Trace|%s' % dump({
                'trace': trace
            }))
            current_file = current['file']
            self.ws.send('Check|%s' % dump({
                'name': current_file,
                'sha512': sha512(self.get_file(current_file)).hexdigest()
            }))
        else:
            self.begun = True

        while True:
            message = self.ws.receive()
            if '|' in message:
                pipe = message.index('|')
                cmd = message[:pipe]
                data = message[pipe + 1:]
            else:
                cmd = message
                data = ''

            log.info('Cmd %s #Data %d' % (cmd, len(data)))
            if cmd == 'Start':
                self.ws.send('Title|%s' % dump({
                    'title': exception,
                    'subtitle': exception_description
                }))
                self.ws.send('Trace|%s' % dump({
                    'trace': trace
                }))
                current_file = current['file']
                self.ws.send('Check|%s' % dump({
                    'name': current_file,
                    'sha512': sha512(self.get_file(current_file)).hexdigest()
                }))

            elif cmd == 'Select':
                current_index = int(data)
                current = trace[current_index]
                current_file = current['file']
                locals = stack[current_index][0].f_locals
                self.ws.send('Check|%s' % dump({
                    'name': current_file,
                    'sha512': sha512(self.get_file(current_file)).hexdigest()
                }))

            elif cmd == 'File':
                current_file = current['file']
                self.ws.send('File|%s' % dump({
                    'file': self.get_file(current_file),
                    'name': current_file,
                    'sha512': sha512(self.get_file(current_file)).hexdigest()
                }))
                self.ws.send('Select|%s' % dump({
                    'frame': current
                }))

            elif cmd == 'NoFile':
                self.ws.send('Select|%s' % dump({
                    'frame': current
                }))

            elif cmd == 'Inspect':
                thing = reverse_id(int(data))
                self.ws.send('Dump|%s' % dump({
                    'for': escape(repr(thing)),
                    'val': escape(pformat({
                        key: getattr(thing, key)
                        for key in dir(thing)}))
                }))

            elif cmd == 'Trace':
                self.ws.send('Trace|%s' % dump(trace))

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
                self.ws.send('Print|%s' % dump({
                    'result': escape('\n'.join(out) + '\n'.join(err))
                }))

            elif cmd == 'Ping':
                self.ws.send('Pong')

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

            elif cmd == 'Quit':
                if hasattr(self, 'botframe'):
                    self.set_continue()
                    self.ws.close()
                break

            else:
                log.warn('Unknown command %s' % cmd)

    def user_call(self, frame, argument_list):
        """This method is called when there is the remote possibility
        that we ever need to stop in this function."""
        if self.stop_here(frame):
            log.warn('CALL')
            self.handle_connection()
            self.ws.send('Echo|%s' % dump({
                'for': '__call__',
                'val': frame.f_code.co_name}))
            # self.interaction(frame, first_step=False)

    def user_line(self, frame):
        """This function is called when we stop or break at this line.""",
        if self.stop_here(frame):
            log.warn('LINE')
            self.handle_connection()
            self.interaction(frame)

    def user_return(self, frame, return_value):
        """This function is called when a return trap is set here."""
        if self.stop_here(frame):
            log.warn('RETURN')
            frame.f_locals['__return__'] = return_value
            self.handle_connection()
            self.ws.send('Echo|%s' % dump({
                'for': '__return__',
                'val': return_value
            }))
            self.interaction(frame)

    def user_exception(self, frame, exc_info):
        """This function is called if an exception occurs,
        but only if we are to stop at or just below this level."""
        log.error('EXCEPTION', exc_info=exc_info)
        type_, value, tb = exc_info
        frame.f_locals['__exception__'] = type_, value
        exception = type_.__name__
        exception_description = str(value)
        self.handle_connection()
        self.ws.send('Echo|%s' % dump({
            'for': '__exception__',
            'val': '%s: %s' % (
            exception, exception_description)}))
        self.interaction(frame, tb, exception, exception_description)


def set_trace(frame=None):
    Wdb.tf(frame or sys._getframe().f_back)
