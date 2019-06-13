#!/usr/bin/env python
import os
import socket
from logging import DEBUG, INFO, WARNING, getLogger

from tornado.ioloop import IOLoop
from tornado.netutil import add_accept_handler, bind_sockets
from tornado.options import options
from tornado_systemd import SYSTEMD_SOCKET_FD, SystemdHTTPServer
from wdb_server import server
from wdb_server.streams import handle_connection

log = getLogger('wdb_server')
if options.debug:
    log.setLevel(INFO)
    if options.more:
        log.setLevel(DEBUG)
else:
    log.setLevel(WARNING)

if os.getenv('LISTEN_PID'):
    log.info('Getting socket from systemd')
    sck = socket.fromfd(
        SYSTEMD_SOCKET_FD + 1,  # Second socket in .socket file
        socket.AF_INET6 if socket.has_ipv6 else socket.AF_INET,
        socket.SOCK_STREAM,
    )
    sck.setblocking(0)
    sck.listen(128)
    sockets = [sck]
else:
    log.info('Binding sockets')
    sockets = bind_sockets(options.socket_port)

log.info('Accepting')
for sck in sockets:
    add_accept_handler(sck, handle_connection)

log.info('Listening')
http_server = SystemdHTTPServer(server)
http_server.listen(options.server_port)

log.info('Starting loop')
IOLoop.current().start()
