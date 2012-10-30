# *-* coding: utf-8 *-*
from bdb import Bdb
from cgi import escape
from json import dumps, loads, JSONEncoder
from linecache import checkcache, getlines
from log_colorizer import get_color_logger
from random import randint
from sys import exc_info
from urlparse import parse_qs
from utils import capture_output, get_trace, tb_to_stack
from websocket import WebSocket
import os
import sys

RES_PATH = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), 'resources')
log = get_color_logger('w')


class NoReceiverInPlace(Exception):
    pass


class What(Exception):
    pass


class ReprEncoder(JSONEncoder):
    def default(self, obj):
        try:
            return JSONEncoder.default(self, obj)
        except TypeError:
            return repr(obj)


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
        if cls._inst_.receiver_in_place:
            log.info('Setting trace')
            Hat(cls._inst_).set_trace(sys._getframe().f_back)
        else:
            log.info('Reloading with receiver')
            raise NoReceiverInPlace


class W(object):
    """W debugger main class"""
    __metaclass__ = M

    @property
    def html(self):
        with open(os.path.join(RES_PATH, 'w.html')) as f:
            return f.read()

    @property
    def html_get(self):
        with open(os.path.join(RES_PATH, 'wget.html')) as f:
            return f.read()

    def __init__(self, app):
        self.app = app
        self.tracebacks = []
        self.vars = []
        tries = 1
        self.receiver_in_place = False
        self.ws = WebSocket('localhost', randint(10000, 60000))
        while self.ws == 'FAIL' and tries < 10:
            tries += 1
            self.ws = WebSocket('localhost', randint(10000, 60000))

    def __call__(self, environ, start_response):
        qs = parse_qs(environ.get('QUERY_STRING', ''))
        if qs.get('__w__', []) == ['__w__']:
            return self.debugger_request(environ, start_response, qs)
        elif (not qs.get('__w', []) == ['tf__'] or
              environ.get('HTTP_W_TYPE') == 'Get'):
            return self.handled_request(environ, start_response)
        else:
            self.receiver_in_place = True
            return self.first_request(environ, start_response, qs)

    def push_trace(self, stack, exc_name, exc_desc, w_code=None, current=None):
        trace, var = get_trace(stack, exc_name, exc_desc, w_code, current)
        trace['id'] = len(self.tracebacks)
        self.tracebacks.append(trace)
        self.vars.append(var)
        return trace

    def handled_request(self, environ, start_response):
        appiter = None
        try:
            appiter = self.app(environ, start_response)
            for item in appiter:
                yield item
            if hasattr(appiter, 'close'):
                appiter.close()
            self.receiver_in_place = False
        except NoReceiverInPlace:
            if hasattr(appiter, 'close'):
                appiter.close()

            start_response('303 SEE OTHER', [
                ('Content-Type', 'text/html'),
                ('Location', '%s?__w=tf__' % environ.get('PATH_INFO'))])
            yield (
                '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n'
                '<title>Redirecting...</title>\n'
                '<h1>Redirecting...</h1>\n'
                '<p>You should be redirected automatically to target '
                '<a href="%s?__w=tf__">URL</a>.  If not click the link.' %
                environ.get('PATH_INFO'))
        except Exception as e:
            if hasattr(appiter, 'close'):
                appiter.close()

            try:
                start_response('500 INTERNAL SERVER ERROR', [
                    ('Content-Type', 'text/html')])
            except:
                pass

            type_, value, tb = exc_info()
            stack = tb_to_stack(tb)
            if isinstance(e, What):
                stack.pop(-1)
            trace = self.push_trace(
                stack, type_.__name__, str(value).title())
            yield self.html.format(
                trace=dumps(trace, cls=ReprEncoder))
            self.receiver_in_place = False

    def first_request(self, environ, start_response, qs):
        start_response('200 OK', [('Content-Type', 'text/html')])
        yield self.html_get.format(port=self.ws.port)

    def debugger_request(self, environ, start_response, qs):
        qs = {key: value[0] if len(value) else None
              for key, value in qs.items() if not key == '__w__'}
        response, type_ = getattr(self, 'w_get_' + qs.pop('what'))(**qs)
        if type_ == 'json':
            response = dumps(response, cls=ReprEncoder)
            mime = 'text/json'
        elif type_ == 'html':
            mime = 'text/html'
        elif type_ == 'js':
            mime = 'text/javascript'
        elif type_ == 'css':
            mime = 'text/css'

        start_response('200 OK', [
            ('Content-Type', mime)])
        yield response

    def w_get_file(self, which=None, **kwargs):
        checkcache(which)
        return {'file': escape(''.join(getlines(which)))}, 'json'

    def w_get_eval(self, who=None, whose=None, where=None, **kwargs):
        env = self.vars[int(whose)][int(where)]
        with capture_output() as (out, err):
            try:
                code = compile(who, '<w>', 'single')
                exec code in env
            except Exception as e:
                type_, value, tb = exc_info()
                stack = tb_to_stack(tb)
                trace = self.push_trace(
                    stack, type_.__name__,
                    str(value).title(), w_code=who)
                return {'result': e, 'exception': trace['id']}, 'json'

        return {'result': escape('\n'.join(out) + '\n'.join(err))}, 'json'

    def w_get_sub_exception(self, which=None, **kwargs):
        trace = self.tracebacks[int(which)]
        return self.html.format(
            trace=dumps(trace, cls=ReprEncoder)), 'html'

    def w_get_resource(self, which=None, **kwargs):
        which = which.strip('/')
        with open(os.path.join(RES_PATH, which)) as f:
            return f.read(), which.split('.')[-1]


class Hat(Bdb):

    def __init__(self, w, skip=None):
        Bdb.__init__(self, skip=skip)
        self.ws = w.ws
        self.connected = False
        self.w = w

    def handle_connection(self):
        if self.connected:
            self.ws.send('PING')
            ret = None
            try:
                ret = self.ws.receive()
            except:
                log.exception('Ping Failed')
            self.connected = ret == 'PONG'

        if not self.connected:
            self.ws.wait_for_connect()
            self.connected = True

    def interaction(self, frame, tb=None):
        stack, i = self.get_stack(frame, tb)
        trace = self.w.push_trace(stack, 'W', 'TF', current=frame)
        self.ws.send('TRACE|' + dumps(trace, cls=ReprEncoder))
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
            if cmd == 'GET':
                data = loads(data)
                response, type_ = getattr(
                    self.w, 'w_get_' + data.pop('what'))(**data)
                if type_ == 'json':
                    self.ws.send('JSON|' + dumps(response, cls=ReprEncoder))
                else:
                    self.ws.send('HTML|' + response)
            elif cmd == 'PING':
                self.ws.send('PONG')
            elif cmd == 'STEP':
                self.set_step()
                break
            elif cmd == 'CONTINUE':
                self.set_continue()
                break
            elif cmd == 'QUIT':
                self.set_quit()
                self.ws.close()
                break
            else:
                log.warn('Unknown command %s' % cmd)

    def user_call(self, frame, argument_list):
        """This method is called when there is the remote possibility
        that we ever need to stop in this function."""
        # if self.stop_here(frame):
        #     self.handle_connection()
        #     self.interaction(frame)

    def user_line(self, frame):
        """This function is called when we stop or break at this line.""",
        if self.stop_here(frame):
            self.handle_connection()
            self.interaction(frame)

    def user_return(self, frame, return_value):
        """This function is called when a return trap is set here."""
        # if self.stop_here(frame):
        #     frame.f_locals['__return__'] = return_value
        #     self.handle_connection()
        #     self.interaction(frame)

    def user_exception(self, frame, exc_info):
        """This function is called if an exception occurs,
        but only if we are to stop at or just below this level."""
