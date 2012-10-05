# import the helper functions we need to get and render tracebacks
from sys import exc_info
from traceback import extract_tb
from json import dumps
import os

with open(os.path.join(os.path.dirname(__file__), 'jquery.min.js')) as f:
    JQUERY = f.read()

with open(os.path.join(os.path.dirname(__file__), 'w.js')) as f:
    W = f.read()


class w(object):
    """w"""

    @property
    def jquery(self):
        with open(os.path.join(
                os.path.dirname(__file__), 'jquery.min.js')) as f:
            jquery = f.read()
        return jquery

    @property
    def w(self):
        with open(os.path.join(os.path.dirname(__file__), 'w.js')) as f:
            w = f.read()
        return w

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        """Catch underlying exceptions"""
        appiter = None
        try:
            appiter = self.app(environ, start_response)
            for item in appiter:
                yield item
        except:
            e_type, e_value, tb = exc_info()
            try:
                start_response('500 INTERNAL SERVER ERROR', [
                               ('Content-Type', 'text/html')])
            except:
                pass

            yield '<!DOCTYPE html>'
            yield '<html>'
            yield '<head>'
            yield '<script type="text/javascript">'
            yield self.jquery
            yield '  _ = %s;' % dumps(extract_tb(tb))
            yield self.w
            yield '</script>'
            yield '</head>'
            yield '<body>'
            yield '</body>'
            yield '</html>'

        if hasattr(appiter, 'close'):
            appiter.close()
