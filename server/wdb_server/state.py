# *-* coding: utf-8 *-*
# This file is part of wdb
#
# wdb Copyright (C) 2012-2015  Florian Mounier, Kozea
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

from tornado.util import unicode_type
from struct import pack
import logging
import json

log = logging.getLogger('wdb_server')


class BaseSockets(object):
    def __init__(self):
        self._sockets = {}

    def send(self, uuid, data, message=None):
        if message:
            data = data + '|' + json.dumps(message)
        if isinstance(data, unicode_type):
            data = data.encode('utf-8')
        sck = self.get(uuid)
        if sck:
            self._send(sck, data)
        else:
            log.warn('No socket found for %s' % uuid)

    def get(self, uuid):
        return self._sockets.get(uuid)

    def broadcast(self, cmd, message=None):
        for uuid in list(self._sockets.keys()):
            try:
                log.debug('Broadcast to socket %s' % uuid)
                self.send(uuid, cmd, message)
            except Exception:
                log.warn('Failed broadcast to socket %s' % uuid)
                self.close(uuid)
                self.remove(uuid)

    def add(self, uuid, sck):
        if uuid in self._sockets:
            self.remove(uuid)
            self.close(uuid)

        self._sockets[uuid] = sck
        syncwebsockets.broadcast(
            'Add' + self.__class__.__name__.rstrip('s'), uuid)

    def remove(self, uuid):
        sck = self._sockets.pop(uuid, None)
        if sck:
            syncwebsockets.broadcast(
                'Remove' + self.__class__.__name__.rstrip('s'), uuid)

    def close(self, uuid):
        sck = self.get(uuid)
        try:
            sck.close()
        except Exception:
            log.warn('Failed close to socket %s' % uuid)

    @property
    def uuids(self):
        return set(self._sockets.keys())


class Sockets(BaseSockets):
    def _send(self, sck, data):
        sck.write(pack("!i", len(data)))
        sck.write(data)


class WebSockets(BaseSockets):
    def _send(self, sck, data):
        if sck.ws_connection:
            sck.write(data)
        else:
            log.warn('Websocket is closed')


class SyncWebSockets(WebSockets):
    # Not really need an uuid here but it avoids duplication
    pass


class Breakpoints(object):
    def __init__(self):
        self._breakpoints = []

    def add(self, brk):
        if brk not in self._breakpoints:
            self._breakpoints.append(brk)
            syncwebsockets.broadcast(
                'AddBreak|' + json.dumps(brk))

    def remove(self, brk):
        if brk in self._breakpoints:
            self._breakpoints.remove(brk)
            syncwebsockets.broadcast(
                'RemoveBreak|' + json.dumps(brk))

    def get(self):
        return self._breakpoints

sockets = Sockets()
websockets = WebSockets()
syncwebsockets = SyncWebSockets()
breakpoints = Breakpoints()
