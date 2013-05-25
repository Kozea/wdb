from uuid import uuid4
from multiprocessing import Pipe
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import os

ioloop = tornado.ioloop.IOLoop.instance()

connection, child_connection = Pipe()


class MainHandler(tornado.web.RequestHandler):
    def get(self, tag):
        self.render('wdb.html', theme='dark', uuid=str(uuid4()))


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def transmit(self):
        try:
            poll = connection.poll()
        except:
            return

        if poll:
            message = connection.recv()
            try:
                self.write_message(message)
            except:
                return
        ioloop.add_callback(self.transmit)

    def open(self, tag):
        self.tag = tag
        connection.send('start')
        ioloop.add_callback(self.transmit)

    def on_message(self, message):
        connection.send(message)

    def on_close(self):
        connection.send('Quit')


server = tornado.web.Application(
    [
        (r"/debug/session/(.+)", MainHandler),
        (r"/websocket/(.+)", WebSocketHandler),
    ],
    debug=True,
    static_path=os.path.join(os.path.dirname(__file__), "static"),
    template_path=os.path.join(os.path.dirname(__file__), "templates")
)
