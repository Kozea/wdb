import sys

python_version = sys.version_info[0]


try:
    from json import loads, dumps, JSONEncoder
except ImportError:
    from simplejson import loads, dumps, JSONEncoder

try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote

try:
    from html import escape
except ImportError:
    from cgi import escape

if python_version == 2:
    from StringIO import StringIO
else:
    from io import StringIO

if python_version == 2:
    def execute(cmd, globals_, locals_):
        exec('exec cmd in globals_, locals_')
else:
    def execute(cmd, globals_, locals_):
        exec(cmd, globals_, locals_)

if python_version == 2:
    import codecs
    import re
    _cookie_search = re.compile("coding[:=]\s*([-\w.]+)").search

    def _detect_encoding(filename):
        import linecache
        lines = linecache.getlines(filename)

        if not lines or lines[0].startswith("\xef\xbb\xbf"):
            return "utf-8"
        magic = _cookie_search("".join(lines[:2]))
        if magic is None:
            return 'utf-8'
        encoding = magic.group(1)
        try:
            codecs.lookup(encoding)
        except LookupError:
            return 'utf-8'
        return encoding

    def to_unicode(string):
        return string.decode('utf-8')

    def to_unicode_string(string, filename):
        encoding = _detect_encoding(filename)
        if encoding != 'utf-8' and string:
            return string.decode(encoding).encode('utf-8')
        else:
            return string

    def to_bytes(string):
        return string

    def from_bytes(bytes_):
        return bytes_

    def force_bytes(bytes_):
        if isinstance(bytes_, unicode):
            return bytes_.encode('utf-8')
        return bytes_
else:
    def to_unicode(string):
        return string

    def to_unicode_string(string, filename):
        return string

    def to_bytes(string):
        return string.encode('utf-8')

    def from_bytes(bytes_):
        return bytes_.decode('utf-8')

    def force_bytes(bytes_):
        if isinstance(bytes_, str):
            return bytes_.encode('utf-8')
        return bytes_


def u(s):
    if python_version == 2:
        return s.decode('utf-8')
    return s


if python_version == 2:
    import struct
    import socket

    class Socket(object):
        """A Socket compatible with multiprocessing.connection.Client, that
        uses socket objects."""
        # https://github.com/akheron/cpython/blob/3.3/Lib/multiprocessing/connection.py#L349
        def __init__(self, address):
            self._handle = socket.socket()
            self._handle.connect(address)
            self._handle.setblocking(1)

        def send_bytes(self, buf):
            self._check_closed()
            n = len(buf)
            # For wire compatibility with 3.2 and lower
            header = struct.pack("!i", n)
            if n > 16384:
                # The payload is large so Nagle's algorithm won't be triggered
                # and we'd better avoid the cost of concatenation.
                chunks = [header, buf]
            elif n > 0:
                # Issue #20540: concatenate before sending, to avoid delays
                # dueto Nagle's algorithm on a TCP socket.
                chunks = [header + buf]
            else:
                # This code path is necessary to avoid "broken pipe" errors
                # when sending a 0-length buffer if the other end closed the
                # pipe.
                chunks = [header]
            for chunk in chunks:
                self._handle.sendall(chunk)

        def recv_bytes(self):
            self._check_closed()
            size, = struct.unpack("!i", self._handle.recv(4))
            return self._handle.recv(size)

        def _check_closed(self):
            if self._handle is None:
                raise IOError("handle is closed")

        def close(self):
            self._check_closed()
            self._handle.close()
            self._handle = None
else:
    from multiprocessing.connection import Client as Socket
