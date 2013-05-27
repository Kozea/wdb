from wdb import trace


class WdbMiddleware(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        appiter = None
        try:
            with trace():
                appiter = self.app(environ, start_response)
                for item in appiter:
                    yield item
        finally:
            hasattr(appiter, 'close') and appiter.close()
