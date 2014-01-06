
from wdb_server import Sockets
from tornado.iostream import IOStream, StreamClosedError
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

            try:
                Sockets.websockets[uuid].write_message('Die')
            except:
                log.warn("Can't tell the browser", exc_info=True)

            try:
                Sockets.websockets[uuid].close()
            except:
                log.warn("Can't close socket", exc_info=True)

        del Sockets.websockets[uuid]
    del Sockets.sockets[uuid]


def read_frame(stream, uuid, frame):
    websocket = Sockets.websockets.get(uuid)
    if websocket:
        if websocket.ws_connection is None:
            log.warn(
                'Connection has been closed but websocket is still in map')
            del Sockets.websockets[uuid]
        else:
            websocket.write(frame)
    else:
        log.error('Web socket is unknown for frame %s' % frame)

    try:
        stream.read_bytes(4, partial(read_header, stream, uuid))
    except StreamClosedError:
        log.warn('Closed stream for %s' % uuid)


def read_header(stream, uuid, length):
    length, = unpack("!i", length)
    try:
        stream.read_bytes(length, partial(read_frame, stream, uuid))
    except StreamClosedError:
        log.warn('Closed stream for %s' % uuid)


def assign_stream(stream, uuid):
    uuid = uuid.decode('utf-8')
    log.debug('Assigning stream to %s' % uuid)
    Sockets.sockets[uuid] = stream
    stream.set_close_callback(partial(on_close, stream, uuid))
    try:
        stream.read_bytes(4, partial(read_header, stream, uuid))
    except StreamClosedError:
        log.warn('Closed stream for %s' % uuid)


def read_uuid_size(stream, length):
    length, = unpack("!i", length)
    assert length == 36, 'Wrong uuid'
    try:
        stream.read_bytes(length, partial(assign_stream, stream))
    except StreamClosedError:
        log.warn('Closed stream for getting uuid')


def handle_connection(connection, address):
    log.info('Connection received from %s' % str(address))
    stream = IOStream(connection, ioloop)
    # Getting uuid
    try:
        stream.read_bytes(4, partial(read_uuid_size, stream))
    except StreamClosedError:
        log.warn('Closed stream for getting uuid length')
