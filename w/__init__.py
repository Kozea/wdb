# *-* coding: utf-8 *-*
from sys import exc_info
from urlparse import parse_qs
from json import dumps, JSONEncoder
from linecache import getlines, getline, checkcache
from utils import capture_output
from websocket import WebSocket
from cgi import escape
from random import randint
from log_colorizer import get_color_logger
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
        Hat(cls._inst_).set_trace(sys._getframe().f_back)


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
        tries = 1
        self.ws = WebSocket('localhost', randint(10000, 60000))
        while self.ws == 'FAIL' and tries < 10:
            tries += 1
            self.ws = WebSocket('localhost', randint(10000, 60000))

    def __call__(self, environ, start_response):
        qs = parse_qs(environ.get('QUERY_STRING', ''))
        if qs.get('__w__', []) == ['__w__']:
            return self.debugger_request(environ, start_response, qs)
        elif qs.get('__h__', []) == ['__at__']:
            return self.handled_request(environ, start_response)
        else:
            return self.first_request(environ, start_response, qs)

    def get_trace(self, type_, value, tb, w_code=None):
        frames = []
        n = 0
        tb = tb.tb_next  # Remove w stack line
        while tb:
            frame = tb.tb_frame
            lno = tb.tb_lineno
            code = frame.f_code
            function_name = code.co_name
            filename = code.co_filename
            if filename == '<w>' and w_code:
                line = w_code
            else:
                checkcache(filename)
                line = getline(filename, lno, frame.f_globals)
                line = line and line.strip()
            frames.append({
                'file': code.co_filename,
                'function': function_name,
                'flno': code.co_firstlineno,
                'lno': lno,
                'code': escape(line),
                'level': n,
                'locals': frame.f_locals,
                'globals': frame.f_globals
            })
            tb = tb.tb_next
            n += 1

        return {
            'type': type_.__name__,
            'value': str(value).title(),
            'frames': frames,
            'locals': locals(),
            'globals': globals()
        }

    def handled_request(self, environ, start_response):
        appiter = None
        try:
            appiter = self.app(environ, start_response)
            for item in appiter:
                yield item
            if hasattr(appiter, 'close'):
                appiter.close()
        except:
            if hasattr(appiter, 'close'):
                appiter.close()

            exec_info = exc_info()
            try:
                start_response('500 INTERNAL SERVER ERROR', [
                               ('Content-Type', 'text/html')])
            except:
                pass

            trace = self.get_trace(*exec_info)
            trace['id'] = len(self.tracebacks)
            self.tracebacks.append(trace)
            yield self.html.format(
                trace=dumps(trace, cls=ReprEncoder))

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

    def w_get_file(self, which=None):
        checkcache(which)
        return {'file': escape(''.join(getlines(which)))}, 'json'

    def w_get_eval(self, who=None, whose=None, where=None):
        frame = self.tracebacks[int(whose)]['frames'][int(where)]

        with capture_output() as (out, err):
            try:
                code = compile(who, '<w>', 'single')
                env = {}
                env.update(frame['globals'])
                env.update(frame['locals'])
                exec code in env, frame['locals']
            except Exception as e:
                exec_info = exc_info()
                trace = self.get_trace(*exec_info, w_code=who)
                trace['id'] = len(self.tracebacks)
                self.tracebacks.append(trace)
                return {'result': e, 'exception': trace['id']}, 'json'

        return {'result': escape('\n'.join(out) + '\n'.join(err))}, 'json'

    def w_get_sub_exception(self, which=None):
        trace = self.tracebacks[int(which)]
        return self.html.format(
            trace=dumps(trace, cls=ReprEncoder)), 'html'

    def w_get_resource(self, which=None):
        which = which.strip('/')
        with open(os.path.join(RES_PATH, which)) as f:
            return f.read(), which.split('.')[-1]


from bdb import Bdb


class Hat(Bdb):

    def __init__(self, w, skip=None):
        Bdb.__init__(self, skip=skip)
        self.ws = w.ws
        self.connected = False
        self.w = w

    def handle_connection(self):
        if not self.connected:
            self.ws.wait_for_connect()
            self.connected = True

    def user_call(self, frame, argument_list):
        """This method is called when there is the remote possibility
        that we ever need to stop in this function."""
        # if self.stop_here(frame):
            # self.handle_connection()
            # self.setup(frame)
            # sys.exit(1)

    def user_line(self, frame):
        """This function is called when we stop or break at this line.""",
        if self.stop_here(frame):
            self.handle_connection()

            self.setup(frame)
            self.print_stack_trace()
            self.ws.send(self.get_stack_trace())
            op = self.ws.receive()
            log.info(op)
            {
                'STEP': self.set_step,
                'NEXT': self.set_next,
                'RETURN': self.set_return,
                'UNTIL': self.set_until,
                'CONTINUE': self.set_continue,
                'QUIT': self.set_quit
            }[op]()

    def user_return(self, frame, return_value):
        """This function is called when a return trap is set here."""
        # if self.stop_here(frame):
            # sys.exit(1)
        # frame.f_locals['__return__'] = return_value

    def user_exception(self, frame, exc_info):
        """This function is called if an exception occurs,
        but only if we are to stop at or just below this level."""
        # if self.stop_here(frame):
            # sys.exit(1)
        # print "USER_EXCEPTION"
        # exc_type, exc_value, exc_traceback = exc_info
        # frame.f_locals['__exception__'] = exc_type, exc_value
        # if type(exc_type) == type(''):
            # exc_type_name = exc_type
        # else:
            # exc_type_name = exc_type.__name__

    def setup(self, frame, traceback=None):
        self.stack, self.curindex = self.get_stack(frame, traceback)
        self.curframe = self.stack[self.curindex][0]
        self.curframe_locals = self.curframe.f_locals

    def print_stack_trace(self):
        try:
            for frame_lineno in self.stack:
                self.print_stack_entry(frame_lineno)
        except KeyboardInterrupt:
            pass

    def print_stack_entry(self, frame_lineno, prompt_prefix='\n->'):
        frame, lineno = frame_lineno
        if frame is self.curframe:
            print '>',
        else:
            print ' ',
        print self.format_stack_entry(frame_lineno,
                                      prompt_prefix)

    def get_stack_trace(self):
        return '\n'.join(self.get_stack_entry(frame_lineno)
                         for frame_lineno in self.stack)

    def get_stack_entry(self, frame_lineno, prompt_prefix='\n->'):
        frame, lineno = frame_lineno
        s = ''
        if frame is self.curframe:
            s += '>'
        return s + self.format_stack_entry(frame_lineno,
                                           prompt_prefix)
