import inspect
import dis


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
    except:
        try:
            return dis.dis(obj)
        except:
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
