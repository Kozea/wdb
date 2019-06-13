# *-* coding: utf-8 *-*
# This file is part of wdb
#
# wdb Copyright (c) 2012-2016  Florian Mounier, Kozea
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

import json
import logging
import os
import sys
from multiprocessing import Process
from uuid import uuid4

import tornado.httpclient
import tornado.options
import tornado.process
import tornado.web
import tornado.websocket
from wdb_server.state import breakpoints, sockets, syncwebsockets, websockets

try:
    import pkg_resources
except ImportError:
    __version__ = "pkg_resources not found on PYTHON_PATH"
else:
    try:
        __version__ = pkg_resources.require('wdb.server')[0].version
    except pkg_resources.DistributionNotFound:
        __version__ = "wdb.server is not installed"

log = logging.getLogger('wdb_server')
static_path = os.path.join(os.path.dirname(__file__), "static")


class HomeHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('home.html')

    def post(self):
        theme = self.request.arguments.get('theme')
        if theme and theme[0]:
            StyleHandler.theme = theme[0].decode('utf-8')
        self.redirect('/')


# This handler is for extern server style access (ie: 500 page)
# Because they cannot know which is the current theme
class StyleHandler(tornado.web.RequestHandler):
    themes = [
        theme.replace('wdb-', '').replace('.css', '')
        for theme in os.listdir(os.path.join(static_path, 'stylesheets'))
        if theme.startswith('wdb-')
    ]

    def get(self):
        self.redirect(self.static_url('stylesheets/wdb-%s.css' % self.theme))


class ActionHandler(tornado.web.RequestHandler):
    def get(self, uuid, action):
        if action == 'close':
            sockets.close(uuid)
            sockets.remove(uuid)
            websockets.close(uuid)
            websockets.remove(uuid)
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
    def get(self, type_, uuid):
        self.render(
            'wdb.html', uuid=uuid, new_version=server.new_version, type_=type_
        )


class BaseWebSocketHandler(tornado.websocket.WebSocketHandler):
    """
    Base class, used for doing the basic host checks before proceeding.
    """

    def open(self, *args, **kwargs):
        protocol = self.request.headers.get(
            'X-Forwarded-Proto', self.request.protocol
        )
        host = '{protocol}://{host}'.format(
            protocol=protocol, host=self.request.headers['Host']
        )
        if self.request.headers['Origin'] != host:
            self.warn('Origin and host are not the same, closing websocket...')
            self.close()
            return

        self.on_open(*args, **kwargs)

    def on_open(self, *args, **kwargs):
        """
        Method that should be overriden, containing the logic that should
        happen when a new websocket connection opens. At this point, the
        connection is already verified.

        Does nothing by default.
        """
        pass


class WebSocketHandler(BaseWebSocketHandler):
    def write(self, message):
        log.debug('socket -> websocket: %s' % message)
        message = message.decode('utf-8')
        if message.startswith('BreakSet|') or message.startswith(
            'BreakUnset|'
        ):
            log.debug('Intercepted break')
            cmd, brk = message.split('|', 1)
            brk = json.loads(brk)
            if not brk['temporary']:
                del brk['temporary']
                if cmd == 'BreakSet':
                    breakpoints.add(brk)
                elif cmd == 'BreakUnset':
                    breakpoints.remove(brk)

        self.write_message(message)

    def on_open(self, uuid):
        self.uuid = uuid

        if isinstance(self.uuid, bytes):
            self.uuid = self.uuid.decode('utf-8')

        if self.uuid in websockets.uuids:
            log.warn(
                'Websocket already opened for %s. Closing previous one'
                % self.uuid
            )
            websockets.send(self.uuid, 'Die')
            websockets.close(uuid)

        if self.uuid not in sockets.uuids:
            log.warn(
                'Websocket opened for %s with no correponding socket'
                % self.uuid
            )
            sockets.send(self.uuid, 'Die')
            self.close()
            return

        log.info('Websocket opened for %s' % self.uuid)
        websockets.add(self.uuid, self)

    def on_message(self, message):
        log.debug('websocket -> socket: %s' % message)
        if message.startswith('Broadcast|'):
            message = message.split('|', 1)[1]
            sockets.broadcast(message)
        else:
            sockets.send(self.uuid, message)

    def on_close(self):
        if hasattr(self, 'uuid'):
            log.info('Websocket closed for %s' % self.uuid)
            if not tornado.options.options.detached_session:
                sockets.send(self.uuid, 'Close')
                sockets.close(self.uuid)


class SyncWebSocketHandler(BaseWebSocketHandler):
    def write(self, message):
        log.debug('server -> syncsocket: %s' % message)
        self.write_message(message)

    def on_open(self):
        self.uuid = str(uuid4())
        syncwebsockets.add(self.uuid, self)
        if not LibPythonWatcher:
            syncwebsockets.send(self.uuid, 'StartLoop')

    def on_message(self, message):
        if '|' in message:
            cmd, data = message.split('|', 1)
        else:
            cmd, data = message, ''

        if cmd == 'ListSockets':
            for uuid in sockets.uuids:
                syncwebsockets.send(
                    self.uuid,
                    'AddSocket',
                    {
                        'uuid': uuid,
                        'filename': sockets.get_filename(uuid)
                        if tornado.options.options.show_filename
                        else '',
                    },
                )
        elif cmd == 'ListWebsockets':
            for uuid in websockets.uuids:
                syncwebsockets.send(self.uuid, 'AddWebSocket', uuid)
        elif cmd == 'ListBreaks':
            for brk in breakpoints.get():
                syncwebsockets.send(self.uuid, 'AddBreak', brk)
        elif cmd == 'RemoveBreak':
            brk = json.loads(data)
            breakpoints.remove(brk)
            # If it was here, it wasn't temporary
            brk['temporary'] = False
            sockets.broadcast('Unbreak', brk)
        elif cmd == 'RemoveUUID':
            sockets.close(data)
            sockets.remove(data)
            websockets.close(data)
            websockets.remove(data)
        elif cmd == 'ListProcesses':
            refresh_process(self.uuid)
        elif cmd == 'Pause':
            if int(data) == os.getpid():
                log.debug('Pausing self')

                def self_shell(variables):
                    # Debugging self
                    import wdb

                    wdb.set_trace()

                Process(target=self_shell, args=(globals(),)).start()

            else:
                log.debug('Pausing %s' % data)
                tornado.process.Subprocess(
                    ['gdb', '-p', data, '-batch']
                    + [
                        "-eval-command=call %s" % hook
                        for hook in [
                            'PyGILState_Ensure()',
                            'PyRun_SimpleString('
                            '"import wdb; wdb.set_trace(skip=1)"'
                            ')',
                            'PyGILState_Release($1)',
                        ]
                    ]
                )
        elif cmd == 'RunFile':
            file_name = data

            def run():
                from wdb import Wdb

                Wdb.get().run_file(file_name)

            Process(target=run).start()
        elif cmd == 'RunShell':

            def run():
                from wdb import Wdb

                Wdb.get().shell()

            Process(target=run).start()

    def on_close(self):
        if hasattr(self, 'uuid'):
            syncwebsockets.remove(self.uuid)


tornado.options.define(
    'theme',
    default="clean",
    help="Wdb theme to use amongst %s" % StyleHandler.themes,
)
tornado.options.define("debug", default=False, help="Debug mode")
tornado.options.define(
    "unminified",
    default=False,
    help="Use the unminified js (for development only)",
)
tornado.options.define(
    "more", default=False, help="Set the debug more verbose"
)
tornado.options.define(
    "detached_session",
    default=False,
    help="Whether to continue program on browser close",
)
tornado.options.define(
    "socket_port",
    default=19840,
    help="Port used to communicate with wdb instances",
)
tornado.options.define(
    "server_port", default=1984, help="Port used to serve debugging pages"
)
tornado.options.define(
    "show_filename",
    default=False,
    help="Whether to show filename in session list",
)
tornado.options.define(
    "extra_search_path",
    default=False,
    help=(
        "Try harder to find the 'libpython*' shared library "
        "at the cost of a slower server startup."
    ),
)

tornado.options.parse_command_line()

from wdb_server.utils import (
    refresh_process,
    LibPythonWatcher,
)  # noqa isort:skip

StyleHandler.theme = tornado.options.options.theme

for l in (
    log,
    logging.getLogger('tornado.access'),
    logging.getLogger('tornado.application'),
    logging.getLogger('tornado.general'),
):
    l.setLevel(10 if tornado.options.options.debug else 30)

if LibPythonWatcher:
    LibPythonWatcher(
        sys.base_prefix if tornado.options.options.extra_search_path else None
    )

server = tornado.web.Application(
    [
        (r"/", HomeHandler),
        (r"/style.css", StyleHandler),
        (r"/(\w+)/session/(.+)", MainHandler),
        (r"/debug/file/(.*)", DebugHandler),
        (r"/websocket/(.+)", WebSocketHandler),
        (r"/status", SyncWebSocketHandler),
    ],
    debug=tornado.options.options.debug,
    static_path=static_path,
    template_path=os.path.join(os.path.dirname(__file__), "templates"),
)

http = tornado.httpclient.HTTPClient()
server.new_version = None


log.debug('Feching wdb_server simple pypi page')
try:
    response = http.fetch(
        'https://pypi.python.org/pypi/wdb.server/json',
        connect_timeout=1,
        request_timeout=1,
    )
    log.debug('Parsing pypi page')
    info = json.loads(response.buffer.read().decode('utf-8'))
    version = info['info']['version']
    if version != __version__:
        server.new_version = version
except Exception:
    pass

# Prevent some weird crash on cleanup
del http
