from struct import pack
import tornado.options
import tornado.web
import tornado.websocket
import os
import logging
from multiprocessing import Process

log = logging.getLogger('wdb_server')
static_path = os.path.join(os.path.dirname(__file__), "static")


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

        theme = self.request.arguments.get('theme')
        if theme and theme[0]:
            StyleHandler.theme = theme[0].decode('utf-8')
        self.redirect('/')


# This handler is for extern server style access (ie: 500 page)
# Because they cannot know which is the current theme
class StyleHandler(tornado.web.RequestHandler):
    themes = [theme.replace('wdb-', '').replace('.css', '')
              for theme in os.listdir(os.path.join(static_path, 'stylesheets'))
              if theme.startswith('wdb-')]

    def get(self):
        self.redirect(
            self.static_url('stylesheets/wdb-%s.css' % self.theme))


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


class SelfHandler(tornado.web.RequestHandler):
    def get(self):
        from multiprocessing import Process

        def self_shell(variables):
            import wdb
            wdb.set_trace()

        Process(target=self_shell, args=(globals(),)).start()


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def send(self, message):
        socket = Sockets.sockets.get(self.uuid)
        if not socket:
            if self.ws_connection:
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


tornado.options.define('theme', default="curve",
                       help="Wdb theme to use amongst %s" %
                       StyleHandler.themes)
tornado.options.define("debug", default=False, help="Debug mode")
tornado.options.define("detached_session", default=False,
                       help="Whether to continue program on browser close")

tornado.options.define("socket_port", default=19840,
                       help="Port used to communicate with wdb instances")
tornado.options.define("server_port", default=1984,
                       help="Port used to serve debugging pages")

tornado.options.parse_command_line()
StyleHandler.theme = tornado.options.options.theme

for l in (log, logging.getLogger('tornado.access'),
          logging.getLogger('tornado.application'),
          logging.getLogger('tornado.general')):
    l.setLevel(10 if tornado.options.options.debug else 30)

server = tornado.web.Application(
    [
        (r"/", IndexHandler),
        (r"/style.css", StyleHandler),
        (r"/uuid/([^/]+)/([^/]+)", ActionHandler),
        (r"/debug/session/(.+)", MainHandler),
        (r"/websocket/(.+)", WebSocketHandler),
        (r"/self", SelfHandler),
    ],
    debug=tornado.options.options.debug,
    static_path=static_path,
    template_path=os.path.join(os.path.dirname(__file__), "templates")
)
