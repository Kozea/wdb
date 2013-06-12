import sys

python_version = sys.version_info[0]

try:
    from json import dumps, JSONEncoder
except ImportError:
    from simplejson import dumps, JSONEncoder

try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote

if python_version == 2:
    def execute(cmd, globals_, locals_):
        exec('exec cmd in globals_, locals_')
else:
    def execute(cmd, globals_, locals_):
        exec(cmd, globals_, locals_)

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


def u(s):
    if python_version == 2:
        return s.decode('utf-8')
    return s
