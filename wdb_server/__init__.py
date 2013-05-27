from struct import pack
import tornado.options
import tornado.web
import tornado.websocket
import os
import logging

log = logging.getLogger('wdb_server')


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('There are currently %d open debuggers and %d browsers.' % (
            len(WebSocketHandler.sockets),
            len(WebSocketHandler.websockets)
        ))


class MainHandler(tornado.web.RequestHandler):
    def get(self, uuid):
        self.render('wdb.html', theme='dark', uuid=uuid)


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    websockets = {}
    sockets = {}

    def send(self, message):
        socket = WebSocketHandler.sockets.get(self.uuid)
        log.info('websocket -> socket: %s' % message)
        data = message.encode('utf-8')
        socket.write(pack("!i", len(data)))
        socket.write(data)

    def open(self, uuid):
        self.uuid = uuid.decode('utf-8')
        log.info('Websocket opened for %s' % self.uuid)
        existing = WebSocketHandler.websockets.get(self.uuid)
        if existing:
            existing.write_message('Die')
            existing.close()
        WebSocketHandler.websockets[self.uuid] = self

    def on_message(self, message):
        self.send(message)

    def on_close(self):
        self.send('Continue')
        WebSocketHandler.sockets.get(self.uuid).close()


server = tornado.web.Application(
    [
        (r"/", IndexHandler),
        (r"/debug/session/(.+)", MainHandler),
        (r"/websocket/(.+)", WebSocketHandler),
    ],
    debug=True,
    static_path=os.path.join(os.path.dirname(__file__), "static"),
    template_path=os.path.join(os.path.dirname(__file__), "templates")
)
