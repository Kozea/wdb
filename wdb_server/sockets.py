
from wdb_server import Sockets
from tornado.iostream import IOStream
from tornado.ioloop import IOLoop
from functools import partial
from logging import getLogger
from struct import unpack
from tornado.options import options


log = getLogger('wdb_server')
log.setLevel(10 if options.debug else 30)


ioloop = IOLoop.instance()


def on_close(stream, uuid):
    # None if the user closed the window
    log.info('uuid %s closed' % uuid)
    if Sockets.websockets.get(uuid):
        if Sockets.websockets[uuid].ws_connection is not None:
            log.info('Telling browser to die')
            Sockets.websockets[uuid].write_message('Die')
            Sockets.websockets[uuid].close()
        del Sockets.websockets[uuid]
    del Sockets.sockets[uuid]


def read_frame(stream, uuid, frame):
    websocket = Sockets.websockets.get(uuid)
    if websocket:
        websocket.write(frame)
    else:
        log.error('Web socket is unknown for frame %s' % frame)
    stream.read_bytes(4, partial(read_header, stream, uuid))


def read_header(stream, uuid, length):
    length, = unpack("!i", length)
    stream.read_bytes(length, partial(read_frame, stream, uuid))


def assign_stream(stream, uuid):
    uuid = uuid.decode('utf-8')
    log.debug('Assigning stream to %s' % uuid)
    Sockets.sockets[uuid] = stream
    stream.set_close_callback(partial(on_close, stream, uuid))
    stream.read_bytes(4, partial(read_header, stream, uuid))


def read_uuid_size(stream, length):
    length, = unpack("!i", length)
    assert length == 36, 'Wrong uuid'
    stream.read_bytes(length, partial(assign_stream, stream))


def handle_connection(connection, address):
    log.info('Connection received from %s' % str(address))
    stream = IOStream(connection, ioloop)
    # Getting uuid
    stream.read_bytes(4, partial(read_uuid_size, stream))
