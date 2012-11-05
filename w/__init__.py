# *-* coding: utf-8 *-*
from bdb import Bdb
from cgi import escape
from json import dumps, loads, JSONEncoder
from linecache import checkcache, getlines, getline
from log_colorizer import get_color_logger
from random import randint
from sys import exc_info
from utils import capture_output, tb_to_stack
from websocket import WebSocket
from mimetypes import guess_type
import os
import sys

RES_PATH = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), 'resources')
log = get_color_logger('w')


class ReprEncoder(JSONEncoder):
    def default(self, obj):
        try:
            return JSONEncoder.default(self, obj)
        except TypeError:
            return repr(obj)
dump = lambda x: dumps(x, cls=ReprEncoder)


class M(type):

    def __init__(cls, name, bases, dict):
        super(M, cls).__init__(name, bases, dict)
        cls._inst_ = None

    def __call__(cls, *args, **kwargs):
        if cls._inst_:
            raise NotImplementedError(
                'One debugger is allowed at a time, '
                '%r already registered' % cls._inst_)

        cls._inst_ = super(M, cls).__call__(*args, **kwargs)
        return cls._inst_

    @property
    def tf(cls):
        log.info('Setting trace')
        cls._inst_.set_trace(sys._getframe().f_back)


class W(object, Bdb):
    """W debugger main class"""
    __metaclass__ = M

    @property
    def html(self):
        with open(os.path.join(RES_PATH, 'w.html')) as f:
            return f.read()

    def __init__(self, app, skip=None):
        Bdb.__init__(self, skip=skip)
        self.app = app
        self.ws = WebSocket('localhost', randint(10000, 60000))
        self.connected = False
        tries = 1
        while self.ws == 'FAIL' and tries < 10:
            tries += 1
            self.ws = WebSocket('localhost', randint(10000, 60000))

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        if path.startswith('/__w/'):
            filename = path.replace('/__w/', '')
            log.info('Getting static "%s"' % filename)
            return self.static_request(
                environ, start_response, filename)
        elif 'text/html' in environ.get('HTTP_ACCEPT', ''):
            log.info('Sending fake page (%s)' % environ['HTTP_ACCEPT'])
            return self.first_request(environ, start_response)
        else:
            log.info('Sending real page (%s)[%s]' % (
                environ.get('HTTP_ACCEPT', ''),  environ.get('HTTP_W_TYPE')))
            return self.handled_request(environ, start_response)

        # elif environ.get('HTTP_W_TYPE') == 'Get':
        #     log.info('Sending real page (Got header)')
        #     return self.handled_request(environ, start_response)
        # else:
        #     log.info('Sending fake page')
        #     return self.first_request(environ, start_response)

    def static_request(self, environ, start_response, filename):
        start_response('200 OK', [('Content-Type', guess_type(filename)[0])])
        with open(os.path.join(RES_PATH, filename)) as f:
            yield f.read()

    def handled_request(self, environ, start_response):
        appiter = None
        try:
            appiter = self.app(environ, start_response)
            for item in appiter:
                yield item
            if hasattr(appiter, 'close'):
                appiter.close()
        except Exception:
            log.exception('w')
            if hasattr(appiter, 'close'):
                appiter.close()

            self.handle_connection()
            type_, value, tb = exc_info()
            exception = type_.__name__
            exception_description = str(value)
            self.interaction(None, tb, False, exception, exception_description)
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
        start_response('200 OK', [('Content-Type', 'text/html')])
        yield self.html.format(port=self.ws.port)

    def get_file(self, filename):
        checkcache(filename)
        return escape(''.join(getlines(filename)))

    def w_get_sub_exception(self, trace_id):
        trace = self.tracebacks[int(trace_id)]
        return self.html.format(
            trace=dumps(trace, cls=ReprEncoder)), 'html'

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
            if filename == '<w>' and w_code:
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
            self, frame, tb=None, first_step=True,
            exception='W', exception_description='TF'):
        stack, trace, current_index = self.get_trace(frame, tb)
        current = trace[current_index]
        if first_step:
            self.ws.send('Trace|%s' % dump({
                'trace': trace
            }))
            self.ws.send('Select|%s' % dump({
                'frame': current
            }))
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
                self.ws.send('Select|%s' % dump({
                    'frame': current
                }))

            elif cmd == 'Select':
                current_index = int(data)
                current = trace[current_index]
                self.ws.send('Select|%s' % dump({
                    'frame': current
                }))

            elif cmd == 'File':
                current_file = current['file']
                self.ws.send('File|%s' % dump({
                    'file': self.get_file(current_file),
                    'name': current_file
                }))
                self.ws.send('Select|%s' % dump({
                    'frame': current
                }))

            elif cmd == 'Trace':
                self.ws.send('Trace|%s' % dump(trace, cls=ReprEncoder))

            elif cmd == 'Eval':
                locals = stack[current_index][0].f_locals
                globals = stack[current_index][0].f_globals
                with capture_output() as (out, err):
                    try:
                        compiled_code = compile(data, '<w>', 'single')
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
                    self.set_quit()
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
            self.ws.send('Echo|%s' % dump({'message': '--Call--'}))
            self.interaction(frame, first_step=False)

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
                'message': 'Return: %s' % return_value
            }))
            self.interaction(frame, first_step=False)

    def user_exception(self, frame, exc_info):
        """This function is called if an exception occurs,
        but only if we are to stop at or just below this level."""
        type_, value, tb = exc_info
        frame.f_locals['__exception__'] = type_, value
        exception = type_.__name__
        exception_description = str(value)
        self.handle_connection()
        self.ws.send('Echo|%s' % dump({'message': 'Exception: %s %s' % (
            exception, exception_description)}))
        self.interaction(frame, tb, True, exception, exception_description)
