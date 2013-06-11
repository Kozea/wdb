from wdb import trace, start_trace, stop_trace, set_trace, Wdb
from wdb.ui import dump
from log_colorizer import get_color_logger
import os
import traceback
import sys


log = get_color_logger('wdb.ext')


def _handle_off(theme, silent=False):
    if not silent:
        log.exception('Exception with wdb off')
    type_, value, tb = sys.exc_info()
    stack = traceback.extract_tb(tb)
    stack.reverse()

    with open(
            os.path.join(
                os.path.abspath(os.path.dirname(__file__)),
                'res',
                '500.html')) as f:
        return f.read() % dict(
            theme=theme,
            trace=traceback.format_exc(),
            title=type_.__name__.replace("'", "\\'").replace('\n', ' '),
            subtitle=str(value).replace("'", "\\'").replace('\n', ' '),
            state='',
            trace_dict=dump({
                'trace': stack,
            })
        )


class WdbMiddleware(object):
    def __init__(self, app, start_disabled=False, theme='dark'):
        self.app = app
        self.theme = theme
        Wdb.enabled = not start_disabled

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')

        if path == '/__wdb/on':
            # Enable wdb
            Wdb.enabled = True
            start_response('200 OK', [('Content-Type', 'text/html')])
            return 'Wdb is now on'

        if Wdb.enabled:
            def trace_wsgi(environ, start_response):
                appiter = None
                try:
                    with trace(close_on_exit=True):
                        appiter = self.app(environ, start_response)
                        for item in appiter:
                            yield item
                except Exception:
                    start_response('500 INTERNAL SERVER ERROR', [
                        ('Content-Type', 'text/html')])
                    yield _handle_off(self.theme)
                finally:
                    hasattr(appiter, 'close') and appiter.close()
            return trace_wsgi(environ, start_response)

        def catch(environ, start_response):
            appiter = None
            try:
                appiter = self.app(environ, start_response)
                for item in appiter:
                    yield item
            except Exception:
                start_response('500 INTERNAL SERVER ERROR', [
                    ('Content-Type', 'text/html')])
                yield _handle_off(self.theme)
            finally:
                # Close set_trace debuggers
                stop_trace(close_on_exit=True)
                hasattr(appiter, 'close') and appiter.close()

        return catch(environ, start_response)


def wdb_tornado(application, start_disabled=False, theme='dark'):
    from tornado.web import RequestHandler, HTTPError
    Wdb.enabled = not start_disabled

    class WdbOn(RequestHandler):
        def get(self):
            Wdb.enabled = True
            self.write('Wdb is now on')
    application.add_handlers(r'.*', ((r'/__wdb/on', WdbOn),))

    old_execute = RequestHandler._execute

    def _wdb_execute(self, transforms):
        from wdb import trace, Wdb
        if Wdb.enabled:
            with trace(close_on_exit=True, below=True):
                old_execute(self, transforms)
        else:
            old_execute(self, transforms)
            # Close set_trace debuggers
            stop_trace(close_on_exit=True)

    RequestHandler._execute = _wdb_execute

    def _wdb_error_writter(self, status_code, **kwargs):
        silent = False
        ex = kwargs.get('exc_info')
        if ex:
            silent = issubclass(ex[0], HTTPError)
        self.finish(_handle_off(theme, silent=silent))

    RequestHandler.write_error = _wdb_error_writter


def add_w_builtin():
    class w(object):
        """Global shortcuts"""

        @property
        def tf(self):
            set_trace(sys._getframe().f_back)

        @property
        def start(self):
            start_trace(sys._getframe().f_back)

        @property
        def stop(self):
            stop_trace(sys._getframe().f_back)

        @property
        def trace(self):
            trace(sys._getframe().f_back)

    __builtins__['w'] = w()
