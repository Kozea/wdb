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
else:
    def to_unicode(string):
        return string

    def to_unicode_string(string, filename):
        return string

    def to_bytes(string):
        return string.encode('utf-8')

    def from_bytes(bytes_):
        return bytes_.decode('utf-8')


def u(s):
    if python_version == 2:
        return s.decode('utf-8')
    return s
