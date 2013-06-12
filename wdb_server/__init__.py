from struct import pack
import tornado.options
import tornado.web
import tornado.websocket
import os
import logging
from multiprocessing import Process

log = logging.getLogger('wdb_server')


class Sockets(object):
    websockets = {}
    sockets = {}


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('index.html')

    def post(self):
        fn = self.request.arguments.get('debug_file')
        if fn and fn[0]:
            def run():
                from wdb import Wdb
                Wdb.get().run_file(fn[0].decode('utf-8'))
            Process(target=run).start()
        self.redirect('/')


class ActionHandler(tornado.web.RequestHandler):
    def get(self, uuid, action):
        if action == 'close':
            socket = Sockets.sockets.get(uuid)
            if socket:
                socket.close()
            else:
                ws = Sockets.websockets.get(uuid)
                if ws:
                    try:
                        ws.close()
                    except:
                        del Sockets.websockets[uuid]
        self.redirect('/')


class MainHandler(tornado.web.RequestHandler):
    def get(self, uuid):
        self.render('wdb.html', uuid=uuid)


class WebSocketHandler(tornado.websocket.WebSocketHandler):

    def send(self, message):
        socket = Sockets.sockets.get(self.uuid)
        if not socket:
            self.close()
            return
        log.debug('websocket -> socket: %s' % message)
        data = message.encode('utf-8')
        socket.write(pack("!i", len(data)))
        socket.write(data)

    def write(self, message):
        log.debug('socket -> websocket: %s' % message)
        self.write_message(message)

    def open(self, uuid):
        self.uuid = uuid.decode('utf-8')
        log.info('Websocket opened for %s' % self.uuid)
        Sockets.websockets[self.uuid] = self

    def on_message(self, message):
        self.send(message)

    def on_close(self):
        log.info('Websocket closed for %s' % self.uuid)
        socket = Sockets.sockets.get(self.uuid)
        if socket and not tornado.options.options.detached_session:
            self.send('Continue')
            socket.close()


tornado.options.define('theme', default="dark", help="wdb theme to use")
tornado.options.define("debug", default=False, help="Debug mode")
tornado.options.define("detached_session", default=False,
                       help="Whether to continue program on browser close")

tornado.options.define("socket_port", default=19840,
                       help="Port used to communicate with wdb instances")
tornado.options.define("server_port", default=1984,
                       help="Port used to serve debugging pages")

tornado.options.parse_command_line()
for l in (log, logging.getLogger('tornado.access'),
          logging.getLogger('tornado.application'),
          logging.getLogger('tornado.general')):
    l.setLevel(10 if tornado.options.options.debug else 30)

server = tornado.web.Application(
    [
        (r"/", IndexHandler),
        (r"/uuid/([^/]+)/([^/]+)", ActionHandler),
        (r"/debug/session/(.+)", MainHandler),
        (r"/websocket/(.+)", WebSocketHandler),
    ],
    debug=tornado.options.options.debug,
    static_path=os.path.join(os.path.dirname(__file__), "static"),
    template_path=os.path.join(os.path.dirname(__file__), "templates")
)
