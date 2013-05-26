#!/usr/bin/env python
from wdb_server import server, WebSocketHandler
from tornado.netutil import bind_sockets, add_accept_handler
from tornado.ioloop import IOLoop
from tornado.iostream import IOStream
from functools import partial
from log_colorizer import get_color_logger
from struct import unpack
import re


log = get_color_logger('wdb_server')
uuid_re = b'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
size_pattern = re.compile(b'<(\d+)>')
ioloop = IOLoop.instance()
log.debug('Binding sockets')
sockets = bind_sockets(18532)


def read_frame(stream, uuid, frame):
    WebSocketHandler.websockets[uuid].write_message(frame)
    stream.read_bytes(4, partial(read_header, stream, uuid))


def read_header(stream, uuid, length):
    length, = unpack("!i", length)
    stream.read_bytes(length, partial(read_frame, stream, uuid))


def assign_stream(stream, uuid):
    uuid = uuid.decode('utf-8')
    log.debug('Assigning stream to %s' % uuid)
    WebSocketHandler.sockets[uuid] = stream
    stream.read_bytes(4, partial(read_header, stream, uuid))


def handle_connection(connection, address):
    log.info('Connection received from %s' % str(address))
    stream = IOStream(connection, ioloop)
    # Getting uuid
    stream.read_until_regex(
        uuid_re,
        partial(assign_stream, stream))


log.debug('Accepting')
for socket in sockets:
    add_accept_handler(socket, handle_connection, ioloop)

log.debug('Listening')
server.listen(2560)

log.debug('Starting loop')
ioloop.start()
