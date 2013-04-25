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
    from cStringIO import StringIO
except ImportError:
    from StringIO  import StringIO
