import inspect
import dis
import sys
from ._compat import StringIO, existing_module


def pretty_frame(frame):
    if frame:
        return '%s <%s:%d>' % (
            frame.f_code.co_name,
            frame.f_code.co_filename,
            frame.f_lineno
        )
    else:
        return 'None'


def get_source(obj):
    try:
        return inspect.getsource(obj)
    except Exception:
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            dis.dis(obj)
            sys.stdout.seek(0)
            rv = sys.stdout.read()
            sys.stdout = old_stdout
            return rv
        except Exception:
            sys.stdout = old_stdout
            return ''


def get_doc(obj):
    doc = inspect.getdoc(obj)
    com = inspect.getcomments(obj)
    if doc and com:
        return '%s\n\n(%s)' % (doc, com)
    elif doc:
        return doc
    elif com:
        return com
    return ''


def executable_line(line):
    line = line.strip()
    return not (
        (not line or (line[0] == '#') or
         (line[:3] == '"""') or
         line[:3] == "'''"))


def get_args(frame):
    code = frame.f_code
    varnames = code.co_varnames
    nargs = code.co_argcount
    locals = frame.f_locals

    # Regular args
    vars = ['%s=%r' % (var, locals[var]) for var in varnames[:nargs]]

    # Var args (*args)
    if frame.f_code.co_flags & 0x4:
        vars.append('*%s=%r' % (
            varnames[nargs], locals[varnames[nargs]]))
        nargs += 1

    if frame.f_code.co_flags & 0x8:
        vars.append('**%s=%r' % (
            varnames[nargs], locals[varnames[nargs]]))
    return ', '.join(vars)


def importable_module(module):
    return existing_module(module)
