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

from wdb_server import Sockets, SyncWebSocketHandler
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
        SyncWebSocketHandler.broadcast('RM_WS|' + uuid)
    del Sockets.sockets[uuid]
    SyncWebSocketHandler.broadcast('RM_S|' + uuid)


def read_frame(stream, uuid, frame):
    websocket = Sockets.websockets.get(uuid)
    if websocket:
        if websocket.ws_connection is None:
            log.warn(
                'Connection has been closed but websocket is still in map')
            del Sockets.websockets[uuid]
            SyncWebSocketHandler.broadcast('RM_WS|' + uuid)
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
    SyncWebSocketHandler.broadcast('NEW_S|' + uuid)
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
