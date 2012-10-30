import sys
from contextlib import contextmanager
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO  import StringIO

from linecache import getline, checkcache
from cgi import escape


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


def tb_to_stack(tb):
    stack = []
    # tb = tb.tb_next  # Remove w stack line
    while tb:
        stack.append((tb.tb_frame, tb.tb_lineno))
        tb = tb.tb_next
    return stack


def get_trace(stack, exc_name, exc_desc, w_code=None, current=None):
    frames = []
    vars = []

    if not current and len(stack):
        current = stack[-1][0]

    for i, (frame, lno) in enumerate(stack):
        code = frame.f_code
        function_name = code.co_name
        filename = code.co_filename
        if filename == '<w>' and w_code:
            line = w_code
        else:
            checkcache(filename)
            line = getline(filename, lno, frame.f_globals)
            line = line and line.strip()
        frames.append({
            'file': code.co_filename,
            'function': function_name,
            'flno': code.co_firstlineno,
            'lno': lno,
            'code': escape(line),
            'level': i,
            'current': frame == current
        })
        env = {}
        env.update(frame.f_globals)
        env.update(frame.f_locals)
        vars.append(env)
    return {
        'type': exc_name,
        'value': exc_desc,
        'frames': frames
    }, vars
