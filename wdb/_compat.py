import sys
import types

python_version = sys.version_info[0]

try:
    from json import dumps, JSONEncoder
except ImportError:
    from simplejson import dumps, JSONEncoder

try:
    from urlparse import parse_qs
except ImportError:
    def parse_qs(qs):
        return dict([x.split("=") for x in qs.split("&")])

try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote

try:
    from socketserver import ThreadingMixIn
except ImportError:
    from SocketServer import ThreadingMixIn

try:
    from http.server import HTTPServer
except ImportError:
    from BaseHTTPServer import HTTPServer

# Bdb old style class problem
if python_version == 2:
    # from _bdbdb import Bdb as BdbOldStyle
    from bdb import Bdb as BdbOldStyle

    class Bdb(BdbOldStyle, object):
        pass
else:
    from bdb import Bdb
    # from ._bdbdb3 import Bdb


if python_version == 2:
    def execute(cmd, globals_, locals_):
        exec('exec cmd in globals_, locals_')
else:
    def execute(cmd, globals_, locals_):
        exec(cmd, globals_, locals_)


def bind(self, method):
    if python_version == 2:
        return types.MethodType(method, self, self.__class__)
    else:
        return types.MethodType(method, self)

if python_version == 2:
    def to_unicode(string):
        return string.decode('utf-8')

    def to_bytes(string):
        return string

    def from_bytes(bytes_):
        return bytes_
else:
    def to_unicode(string):
        return string

    def to_bytes(string):
        return string.encode('utf-8')

    def from_bytes(bytes_):
        return bytes_.decode('utf-8')


def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    return meta("NewBase", bases, {})
