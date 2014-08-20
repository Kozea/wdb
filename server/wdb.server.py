#!/usr/bin/env python
from wdb_server import server
from tornado.ioloop import IOLoop
from tornado.options import options
from tornado_systemd import SystemdHTTPServer, SYSTEMD_SOCKET_FD
from wdb_server.streams import handle_connection
from tornado.netutil import bind_sockets, add_accept_handler
from logging import getLogger
import socket
import os

log = getLogger('wdb_server')
log.setLevel(10 if options.debug else 30)

ioloop = IOLoop.instance()

if os.getenv('LISTEN_PID'):
    log.debug('Getting socket from systemd')
    sck = socket.fromfd(
        SYSTEMD_SOCKET_FD + 1,  # Second socket in .socket file
        socket.AF_INET6 if socket.has_ipv6 else socket.AF_INET,
        socket.SOCK_STREAM)
    sck.setblocking(0)
    sck.listen(128)
    sockets = [sck]
else:
    log.debug('Binding sockets')
    sockets = bind_sockets(options.socket_port)

log.debug('Accepting')
for sck in sockets:
    add_accept_handler(sck, handle_connection, ioloop)


log.debug('Listening')
http_server = SystemdHTTPServer(server)
http_server.listen(options.server_port)

log.debug('Starting loop')
ioloop.start()
