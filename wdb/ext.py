from wdb import trace, start_trace, stop_trace, set_trace


class WdbMiddleware(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        appiter = None
        try:
            with trace(below=True, close_on_exit=True):
                appiter = self.app(environ, start_response)

            for item in appiter:
                yield item
        finally:
            hasattr(appiter, 'close') and appiter.close()


def wdb_tornado():
    from tornado.web import RequestHandler

    old_execute = RequestHandler._execute

    def _wdb_execute(self, transforms, *args, **kwargs):
        from wdb import trace
        with trace(below=True, close_on_exit=True):
            old_execute(self, transforms, *args, **kwargs)

    RequestHandler._execute = _wdb_execute


def add_w_builtin():
    class w(object):
        """Global shortcuts"""
        tf = set_trace
        start = start_trace
        stop = stop_trace
        trace = trace

    __builtins__['w'] = w
