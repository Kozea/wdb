# import the helper functions we need to get and render tracebacks
from sys import exc_info
from urlparse import parse_qs
from json import dumps, JSONEncoder
from linecache import getlines, getline, checkcache
from StringIO import StringIO
import os
import sys


class ReprEncoder(JSONEncoder):
    def default(self, obj):
        try:
            return JSONEncoder.default(self, obj)
        except TypeError:
            return repr(obj)


class w(object):
    """w"""

    @property
    def html(self):
        with open(os.path.join(
                os.path.abspath(os.path.dirname(__file__)),
                'w.html')) as f:
            return f.read()

    @property
    def js(self):
        js_files = ['jquery.min', 'XRegExp', 'shCore', 'shBrushPython', 'w']
        js = []
        for file in js_files:
            with open(os.path.join(
                    os.path.abspath(os.path.dirname(__file__)),
                    file + '.js')) as f:
                js.append(f.read())
        return '\n'.join(js)

    @property
    def css(self):
        css_files = ['shCore', 'shThemeDefault', 'w']
        css = []
        for file in css_files:
            with open(os.path.join(
                    os.path.abspath(os.path.dirname(__file__)),
                    file + '.css')) as f:
                css.append(f.read())
        return '\n'.join(css)

    def __init__(self, app):
        self.app = app
        self.tracebacks = []

    def __call__(self, environ, start_response):
        """Catch underlying exceptions"""
        qs = parse_qs(environ.get('QUERY_STRING', ''))
        if qs.get('__w__', []) == ['__w__']:
            return self.debugger_request(environ, start_response, qs)
        else:
            return self.handled_request(environ, start_response)

    def get_trace(self, type_, value, tb):
        frames = []
        n = 0
        tb = tb.tb_next  # Remove w stack line
        while tb:
            frame = tb.tb_frame
            lno = tb.tb_lineno
            code = frame.f_code
            function_name = code.co_name
            filename = code.co_filename
            checkcache(filename)
            line = getline(filename, lno, frame.f_globals)
            line = line and line.strip()
            frames.append({
                'file': code.co_filename,
                'function': function_name,
                'lno': lno,
                'code': line,
                'level': n,
                'locals': frame.f_locals,
                'globals': frame.f_globals
            })
            tb = tb.tb_next
            n += 1
        return {
            'type': type_.__name__,
            'value': ' '.join(value).title(),
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
                trace=dumps(trace, cls=ReprEncoder),
                js=self.js,
                css=self.css)

    def debugger_request(self, environ, start_response, qs):
        qs = {key: value[0] if len(value) else None
              for key, value in qs.items() if not key == '__w__'}
        json = dumps(getattr(self, 'w_get_' + qs.pop('what'))(**qs),
                     cls=ReprEncoder)
        start_response('200 OK', [
            ('Content-Type', 'text/json')])
        yield json

    def w_get_file(self, which=None):
        checkcache(which)
        return {'file': ''.join(getlines(which))}

    def w_get_eval(self, who=None, whose=None, where=None):
        frame = self.tracebacks[int(whose)]['frames'][int(where)]
        print who
        out = sys.stdout
        sys.stdout = StringIO()
        code = compile(who, '<w>', 'single')
        env = {}
        env.update(frame['globals'])
        env.update(frame['locals'])
        exec code in env, frame['locals']
        sys.stdout.seek(0)
        read = sys.stdout.read()
        sys.stdout = out
        return {'result': read}
