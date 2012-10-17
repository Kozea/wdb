import sys
from contextlib import contextmanager
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO  import StringIO


@contextmanager
def capture_output():
    stdout, stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = StringIO(), StringIO()
    out, err = [], []
    try:
        yield out, err
    finally:
        out.extend(sys.stdout.getvalue().splitlines())
        err.extend(sys.stderr.getvalue().splitlines())
        sys.stdout, sys.stderr = stdout, stderr
