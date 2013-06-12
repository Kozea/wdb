#!/usr/bin/env python
from wdb_server import server
from tornado.ioloop import IOLoop
from tornado.options import options
from wdb_server.sockets import handle_connection
from tornado.netutil import bind_sockets, add_accept_handler
from logging import getLogger


log = getLogger('wdb_server')
log.setLevel(10 if options.debug else 30)


ioloop = IOLoop.instance()

log.debug('Binding sockets')
sockets = bind_sockets(options.socket_port)

log.debug('Accepting')
for socket in sockets:
    add_accept_handler(socket, handle_connection, ioloop)


log.debug('Listening')
server.listen(options.server_port)

log.debug('Starting loop')
ioloop.start()
