# *-* coding: utf-8 *-*
# This file is part of wdb
#
# wdb Copyright (C) 2012  Florian Mounier, Kozea
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

from log_colorizer import get_color_logger
from StringIO import StringIO
import array
import atexit
import base64
import hashlib
import socket
import struct
import sys

log = get_color_logger('wdb-socket')
log.setLevel(30)

OPCODES = ['continuation', 'text', 'binary',
           '?', '?', '?', '?', '?',
           'close', 'ping', 'pong',
           '?', '?', '?', '?', '?']


class WsError(Exception):
    pass


class WsClosed(WsError):
    pass


class WsBroken(WsError):
    pass


class WsUnavailable(WsError):
    pass


class WsHeader(object):
    expected_fields = {
        'Host': 'host',
        # 'Upgrade': 'upgrade', # Firefox...
        'Connection': 'connection',
        'Sec-WebSocket-Key': 'key',
        'Sec-WebSocket-Version': 'version',
    }
    optional_fields = {
        'Origin': 'origin',
        'Sec-WebSocket-Protocol': 'protocol',
        'Sec-WebSocket-Extensions': 'extensions'
    }

    def __init__(self, header):
        assert header[-4:] == '\r\n\r\n'
        lines = header[:-4].split('\r\n')
        self.method, self.path, self.http = lines[0].split(' ')
        self._fields = {}
        for line in lines[1:-1]:
            key, value = line.split(': ')
            self._fields[key] = value

        for key, name in self.expected_fields.items():
            assert key in self._fields
            setattr(self, name, self._fields[key])

        for key, name in self.optional_fields.items():
            setattr(self, name, self._fields.get(key, None))


class WsFrame(object):

    @staticmethod
    def from_socket(get):
        frame = WsFrame()

        def unpack(format, bytes):
            return struct.unpack(format, bytes)

        header, payload = unpack("BB", get(2))

        frame.fin = header & 0x80
        frame.opcode = header & 0x0f
        frame.type = OPCODES[frame.opcode]
        assert payload & 0x80  # Masking key

        frame.payload_len = payload & 0x7f
        if frame.payload_len == 0x7e:
            frame.payload_len, = unpack('!H', get(2))
        elif frame.payload_len == 0x7f:
            frame.payload_len, = unpack('!Q', get(8))

        frame.mask = array.array("B", get(4))
        frame.data = array.array("B", get(frame.payload_len))
        for i in xrange(len(frame.data)):
            frame.data[i] = frame.data[i] ^ frame.mask[i % 4]
        return frame

    @staticmethod
    def from_data(data):
        frame = WsFrame()

        frame.fin = 0x80  # Final frame
        frame.type = 'text'
        frame.opcode = OPCODES.index(frame.type)  # Text
        header = struct.pack("B", frame.fin | frame.opcode)

        payload_len = len(data)
        if payload_len < 126:
            payload = struct.pack("B", payload_len)
        elif payload_len <= 0xFFFF:
            payload = struct.pack("!BH", 126, payload_len)
        else:
            payload = struct.pack("!BQ", 127, payload_len)

        frame.data = header + payload + data
        return frame

    @staticmethod
    def close():
        frame = WsFrame()

        frame.fin = 0x80  # Final frame
        frame.type = 'close'
        frame.opcode = OPCODES.index(frame.type)  # Text
        header = struct.pack("B", frame.fin | frame.opcode)
        payload = struct.pack("B", 0)

        frame.data = header + payload
        return frame


class WsPacket(object):

    def __init__(self, wssocket, send=None, close=False):
        self.close = False
        if not send and not close:  # Receive mode
            frame = WsFrame.from_socket(wssocket._get)
            self.data = frame.data
            while not frame.fin and not frame.type == 'close':
                frame = WsFrame.from_socket(wssocket._get)
                self.data += frame.data
            if frame.type == 'close':
                self.close = True
            else:
                self.data = self.data.tostring().decode("utf-8")
        elif send:  # Send mode
            self.data = send.encode("utf-8")
            wssocket._send(WsFrame.from_data(self.data).data)

        elif close:
            wssocket._send(WsFrame.close().data)


class WebSocket(object):

    def __init__(self, host, port):
        log.info('Creating websocket on %s:%d' % (host, port))
        self.host = host
        self.port = port
        self.stream = StringIO()
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.handshaken = False
            self.sock.settimeout(1)
            self.sock.bind((self.host, self.port))
            self.sock.listen(0)
        except socket.error:
            log.warn('Port %d is already taken' % port)
            self.status = 'FAIL'
        else:
            log.debug('Listening on %s:%d' % (host, port))
            self.status = 'OK'
        atexit.register(lambda: self.force_close())

    def force_close(self):
        log.debug("Force closing")
        try:
            self.sock.shutdown(1)
            self.sock.close()
        except:
            pass

    def _recv(self):
        try:
            packet = self.peer.recv(4096)
        except:
            log.exception('[%d] Error on socket receive' % self.port)
            raise WsBroken()
        cur = self.stream.tell()
        self.stream.read()  # Seek end
        self.stream.write(packet)
        self.stream.seek(cur)

    def _get(self, size):
        message = self.stream.read(size)

        while len(message) < size:
            # Stream has been all read, clean it up
            self.stream.close()
            del self.stream
            self.stream = StringIO()
            self._recv()
            part = self.stream.read(size - len(message))
            if part == '':
                raise WsClosed()
            message += part
        return message

    def _send(self, data):
        try:
            self.peer.sendall(data)
        except:
            log.exception('[%d] Error on socket send' % self.port)
            raise WsBroken()

    def handshake(self, header):
        sha1 = hashlib.sha1()
        sha1.update(header.key)
        sha1.update("258EAFA5-E914-47DA-95CA-C5AB0DC85B11")
        return (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Accept: %s\r\n"
            "\r\n"
        ) % base64.b64encode(sha1.digest())

    def recv_header(self):
        h = ''
        while h.find('\r\n\r\n') == -1:
            h += self.peer.recv(16)
        return WsHeader(h)

    def wait_for_connect(self):
        log.debug('Waiting for accept')
        try:
            self.peer, self.info = self.sock.accept()
        except:
            log.exception('[%d] Error on socket accept' % self.port)
            raise WsUnavailable
        log.debug('Handshaking with peer %r' % self.peer)
        header = self.recv_header()
        self.peer.sendall(self.handshake(header))
        log.debug('Handshaken')

    def receive(self):
        log.debug('Receiving')
        packet = WsPacket(self)
        log.debug('Received: %s' % packet.data)
        if packet.close:
            log.debug('Close packet')
            WsPacket(self, close=True)
            return 'CLOSED'
        return packet.data

    def send(self, data):
        log.debug('Sending packet: #%d' % len(data))
        WsPacket(self, send=data)
        log.debug('Sent')

    def close(self):
        log.debug('Try Closing')
        WsPacket(self, close=True)
        log.debug('Closing')
        WsPacket(self)
        self.peer.close()
        log.debug('Closed')


if __name__ == '__main__':
    print "Connecting to : localhost:%s" % sys.argv[1]
    ws = WebSocket('localhost', int(sys.argv[1]))
    print "Waiting for connect"
    ws.wait_for_connect()
    print "Connected !"
    print "Waiting for data"
    data = ''
    while data != 'CLOSED':
        data = ws.receive()
        print data
        ws.send(data)
        if data == 'abort':
            ws.close()
            break
