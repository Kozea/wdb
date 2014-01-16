# *-* coding: utf-8 *-*
# This file is part of wdb
#
# wdb Copyright (C) 2012-2014  Florian Mounier, Kozea
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from struct import pack
import tornado.options
import tornado.web
import tornado.websocket
import os
import logging
import pickle
from multiprocessing import Process

log = logging.getLogger('wdb_server')
static_path = os.path.join(os.path.dirname(__file__), "static")
global_breakpoints = set()


class Sockets(object):
    websockets = {}
    sockets = {}


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('index.html')

    def post(self):
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
                        SyncWebSocketHandler.broadcast('RM_WS|' + uuid)
        self.redirect('/')


class BreakpointHandler(tornado.web.RequestHandler):
    def get(self, bpid, action):
        if action == 'delete':
            for breakpoint in list(global_breakpoints):
                if id(breakpoint) == int(bpid):
                    global_breakpoints.remove(breakpoint)
        self.redirect('/')


class DebugHandler(tornado.web.RequestHandler):
    def debug(self, fn):
        def run():
            from wdb import Wdb
            Wdb.get().run_file(fn)
        Process(target=run).start()
        self.redirect('/')

    def get(self, fn):
        self.debug(fn)

    def post(self, fn):
        fn = self.request.arguments.get('debug_file')
        if fn and fn[0]:
            self.debug(fn[0].decode('utf-8'))


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
        if message.startswith(b'Server|'):
            message = message.replace(b'Server|', b'')
            if message == b'GetBreaks':
                socket = Sockets.sockets.get(self.uuid)
                bps = pickle.dumps(global_breakpoints)
                socket.write(pack("!i", len(bps)))
                socket.write(bps)
            if message.startswith(b'AddBreak|'):
                global_breakpoints.add(pickle.loads(
                    message.replace(b'AddBreak|', b'')))
            if message.startswith(b'RmBreak|'):
                global_breakpoints.remove(pickle.loads(
                    message.replace(b'RmBreak|', b'')))
        else:
            self.write_message(message)

    def open(self, uuid):
        self.uuid = uuid.decode('utf-8')
        log.info('Websocket opened for %s' % self.uuid)
        Sockets.websockets[self.uuid] = self
        SyncWebSocketHandler.broadcast('NEW_WS|' + self.uuid)

    def on_message(self, message):
        self.send(message)

    def on_close(self):
        log.info('Websocket closed for %s' % self.uuid)
        socket = Sockets.sockets.get(self.uuid)
        if socket and not tornado.options.options.detached_session:
            self.send('Continue')
            socket.close()


class SyncWebSocketHandler(tornado.websocket.WebSocketHandler):
    websockets = set()

    @staticmethod
    def broadcast(message):
        for ws in set(SyncWebSocketHandler.websockets):
            try:
                ws.write_message(message)
            except:
                SyncWebSocketHandler.websockets.remove(ws)

    def open(self):
        SyncWebSocketHandler.websockets.add(self)

    def on_message(self, message):
        pass

    def on_close(self):
        SyncWebSocketHandler.websockets.remove(self)


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
        (r"/debug/file/(.*)", DebugHandler),
        (r"/breakpoint/(\d+)/([^/]+)", BreakpointHandler),
        (r"/websocket/(.+)", WebSocketHandler),
        (r"/status", SyncWebSocketHandler),
        (r"/self", SelfHandler),
    ],
    debug=tornado.options.options.debug,
    static_path=static_path,
    template_path=os.path.join(os.path.dirname(__file__), "templates")
)
