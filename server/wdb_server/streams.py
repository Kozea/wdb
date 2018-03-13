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
from functools import partial
from logging import getLogger
from struct import unpack

from tornado.iostream import IOStream, StreamClosedError
from tornado.options import options
from wdb_server.state import breakpoints, sockets, websockets

log = getLogger('wdb_server')
log.setLevel(10 if options.debug else 30)


def on_close(stream, uuid):
    # None if the user closed the window
    log.info('uuid %s closed' % uuid)
    if websockets.get(uuid):
        websockets.send(uuid, 'Die')
        websockets.close(uuid)
        websockets.remove(uuid)
    sockets.remove(uuid)


def read_frame(stream, uuid, frame):
    decoded_frame = frame.decode('utf-8')
    if decoded_frame == 'ServerBreaks':
        sockets.send(uuid, json.dumps(breakpoints.get()))
    elif decoded_frame == 'PING':
        log.info('%s PONG' % uuid)
    elif decoded_frame.startswith('UPDATE_FILENAME'):
        filename = decoded_frame.split('|', 1)[1]
        sockets.set_filename(uuid, filename)
    else:
        websockets.send(uuid, frame)
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
    sockets.add(uuid, stream)
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
    stream = IOStream(connection, max_buffer_size=1024 * 1024 * 1024)
    # Getting uuid
    try:
        stream.read_bytes(4, partial(read_uuid_size, stream))
    except StreamClosedError:
        log.warn('Closed stream for getting uuid length')
