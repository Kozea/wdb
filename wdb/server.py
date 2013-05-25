from multiprocessing import Pipe
import tornado.options
import tornado.web
import tornado.websocket
import os

connection, child_connection = Pipe()


class MainHandler(tornado.web.RequestHandler):
    def get(self, uuid):
        self.render('wdb.html', theme='dark', uuid=uuid)


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    clients = {}

    def open(self, uuid):
        self.uuid = uuid.decode('utf-8')
        existing = WebSocketHandler.clients.get(self.uuid)
        if existing:
            existing.write_message('Die')
            existing.close()
        WebSocketHandler.clients[self.uuid] = self
        connection.send('start')

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
