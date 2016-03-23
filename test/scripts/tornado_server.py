from wdb.ext import wdb_tornado

import tornado.ioloop
import tornado.web


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        a = 2
        b = -2
        c = 1 / (a + b) < 0  # <strong> Err œ
        print(c <b> a)
        relay_error()
        self.write("Hello, world")


class OkHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Ok")


def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
    ])

if __name__ == "__main__":
    app = make_app()
    wdb_tornado(app, start_disabled=True)
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
