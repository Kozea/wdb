import dis
import inspect
import io
import os
import signal
import sys
from contextlib import contextmanager
from difflib import HtmlDiff, _mdiff

from ._compat import OrderedDict, StringIO, existing_module


def pretty_frame(frame):
    if frame:
        return '%s <%s:%d>' % (
            frame.f_code.co_name,
            frame.f_code.co_filename,
            frame.f_lineno,
        )
    else:
        return 'None'


def get_code(obj):
    if hasattr(obj, '__func__'):
        return obj.__func__
    if hasattr(obj, '__code__'):
        return obj.__code__
    if hasattr(obj, 'gi_code'):
        return obj.gi_code
    if hasattr(obj, 'co_code'):
        return obj


def get_source_from_byte_code(code):
    try:
        import uncompyle6
    except Exception:
        return
    version = sys.version_info[0] + (sys.version_info[1] / 10.0)
    try:
        with open(os.devnull, 'w') as dn:
            return uncompyle6.deparse_code(version, code, dn).text
    except Exception:
        return


def get_source(obj):
    try:
        return inspect.getsource(obj)
    except Exception:
        code = get_code(obj)
        if code:
            source = get_source_from_byte_code(code)
            if source:
                return (
                    '# The following source has been decompilated:\n' + source
                )

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
        (
            not line
            or (line[0] == '#')
            or (line[:3] == '"""')
            or line[:3] == "'''"
        )
    )


def get_args(frame):
    code = frame.f_code
    varnames = code.co_varnames
    nargs = code.co_argcount
    if hasattr(code, 'co_kwonlyargcount'):
        kwonly = code.co_kwonlyargcount
    else:
        # Python 2
        kwonly = 0
    locals = frame.f_locals

    # Regular args
    vars = OrderedDict([(var, locals[var]) for var in varnames[:nargs]])

    # Var args (*args)
    if frame.f_code.co_flags & 0x4:
        vars['*' + varnames[nargs + kwonly]] = locals[varnames[nargs + kwonly]]
        nargs += 1

    for n in range(kwonly):
        vars[varnames[nargs + n - 1]] = locals[varnames[nargs + n - 1]]

    nargs += kwonly

    if frame.f_code.co_flags & 0x8:
        vars['**' + varnames[nargs]] = locals[varnames[nargs]]

    return vars


def importable_module(module):
    return existing_module(module)


class Html5Diff(HtmlDiff):
    _table_template = """
      <table class="diff">
        %(header_row)s
        <tbody>
          %(data_rows)s
        </tbody>
      </table>"""

    def _format_line(self, side, flag, linenum, text):
        """Returns HTML markup of "from" / "to" text lines

        side -- 0 or 1 indicating "from" or "to" text
        flag -- indicates if difference on line
        linenum -- line number (used for line number column)
        text -- line text to be marked up
        """
        try:
            linenum = '%d' % linenum
            id = ' id="%s%s"' % (self._prefix[side], linenum)
        except TypeError:
            # handle blank lines where linenum is '>' or ''
            id = ''
        # replace those things that would get confused with HTML symbols
        text = (
            text.replace("&", "&amp;")
            .replace(">", "&gt;")
            .replace("<", "&lt;")
        )

        type_ = 'neutral'
        if '\0+' in text:
            type_ = 'add'
        if '\0-' in text:
            if type_ == 'add':
                type_ = 'chg'
            type_ = 'sub'
        if '\0^' in text:
            type_ = 'chg'

        # make space non-breakable so they don't get compressed or line wrapped
        text = text.replace(' ', '&nbsp;').rstrip()

        return (
            '<td class="diff_lno"%s>%s</td>'
            '<td class="diff_line diff_line_%s">%s</td>'
            % (id, linenum, type_, text)
        )

    def make_table(
        self,
        fromlines,
        tolines,
        fromdesc='',
        todesc='',
        context=False,
        numlines=5,
    ):
        """Returns HTML table of side by side comparison with change highlights

        Arguments:
        fromlines -- list of "from" lines
        tolines -- list of "to" lines
        fromdesc -- "from" file column header string
        todesc -- "to" file column header string
        context -- set to True for contextual differences (defaults to False
            which shows full differences).
        numlines -- number of context lines.  When context is set True,
            controls number of lines displayed before and after the change.
            When context is False, controls the number of lines to place
            the "next" link anchors before the next change (so click of
            "next" link jumps to just before the change).
        """

        # make unique anchor prefixes so that multiple tables may exist
        # on the same page without conflict.
        self._make_prefix()

        # change tabs to spaces before it gets more difficult after we insert
        # markup
        fromlines, tolines = self._tab_newline_replace(fromlines, tolines)

        # create diffs iterator which generates side by side from/to data
        if context:
            context_lines = numlines
        else:
            context_lines = None
            diffs = _mdiff(
                fromlines,
                tolines,
                context_lines,
                linejunk=self._linejunk,
                charjunk=self._charjunk,
            )

        # set up iterator to wrap lines that exceed desired width
        if self._wrapcolumn:
            diffs = self._line_wrapper(diffs)

        # collect up from/to lines and flags into lists (also format the lines)
        fromlist, tolist, flaglist = self._collect_lines(diffs)

        # process change flags, generating middle column of next anchors/links
        fromlist, tolist, flaglist, next_href, next_id = self._convert_flags(
            fromlist, tolist, flaglist, context, numlines
        )

        s = []
        fmt = ' <tr>%s%s</tr>\n'

        for i in range(len(flaglist)):
            if flaglist[i] is None:
                # mdiff yields None on separator lines skip the bogus ones
                # generated for the first line
                if i > 0:
                    s.append('        </tbody>        \n        <tbody>\n')
            else:
                s.append(fmt % (fromlist[i], tolist[i]))
        if fromdesc or todesc:
            header_row = '<thead><tr>%s%s</tr></thead>' % (
                '<th colspan="2" class="diff_header">%s</th>' % fromdesc,
                '<th colspan="2" class="diff_header">%s</th>' % todesc,
            )
        else:
            header_row = ''

        table = self._table_template % dict(
            data_rows=''.join(s), header_row=header_row, prefix=self._prefix[1]
        )

        return (
            table.replace('\0+', '<span class="diff_add">')
            .replace('\0-', '<span class="diff_sub">')
            .replace('\0^', '<span class="diff_chg">')
            .replace('\1', '</span>')
            .replace('\t', '&nbsp;')
        )


def search_key_in_obj(key, obj, matches=None, path='', context=None):
    context = context or []
    matches = matches or []
    if id(obj) in context:
        return matches
    context.append(id(obj))

    if isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str):
                continue
            if isinstance(v, type(sys)):
                continue
            if key in k:
                matches.append(
                    (
                        "%s['%s']"
                        % (
                            path.rstrip('.'),
                            k.replace(key, '<mark>%s</mark>' % key),
                        ),
                        v,
                    )
                )
            try:
                matches = search_key_in_obj(
                    key,
                    v,
                    matches,
                    "%s['%s']." % (path.rstrip('.'), k),
                    context,
                )
            except Exception:
                pass

    if isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, type(sys)):
                continue
            try:
                matches = search_key_in_obj(
                    key, v, matches, "%s[%d]." % (path.rstrip('.'), i), context
                )
            except Exception:
                pass

    for k in dir(obj):
        if k.startswith('__') and k not in ('__class__',):
            continue
        v = getattr(obj, k, None)
        v2 = getattr(obj, k, None)
        if id(v) != id(v2):
            continue
        if isinstance(v, type(sys)):
            continue
        if key in k:
            matches.append(
                ('%s%s' % (path, k.replace(key, '<mark>%s</mark>' % key)), v)
            )
        try:
            matches = search_key_in_obj(
                key, v, matches, '%s%s.' % (path, k), context
            )
        except Exception:
            pass

    return matches


def search_value_in_obj(fun, obj, matches=None, path='', context=None):
    context = context or []
    matches = matches or []
    if id(obj) in context:
        return matches
    context.append(id(obj))

    if isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str):
                continue
            if isinstance(v, type(sys)):
                continue

            res = None
            try:
                res = eval(fun, {'x': v})
            except Exception:
                pass
            new_path = "%s['%s']" % (path.rstrip('.'), k)

            if res:
                matches.append((new_path, v))
            try:
                matches = search_value_in_obj(
                    fun, v, matches, new_path + '.', context
                )
            except Exception:
                pass

    if isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, type(sys)):
                continue

            res = None
            try:
                res = eval(fun, {'x': v})
            except Exception:
                pass

            new_path = "%s[%d]" % (path.rstrip('.'), i)

            if res:
                matches.append((new_path, v))
            try:
                matches = search_value_in_obj(
                    fun, v, matches, new_path + '.', context
                )
            except Exception:
                pass

    for k in dir(obj):
        if k.startswith('__') and k not in ('__class__',):
            continue
        v = getattr(obj, k, None)
        v2 = getattr(obj, k, None)
        if id(v) != id(v2):
            continue
        if isinstance(v, type(sys)):
            continue

        res = None
        try:
            res = eval(fun, {'x': v})
        except Exception:
            pass

        new_path = '%s%s' % (path, k)

        if res:
            matches.append((new_path, v))
        try:
            matches = search_value_in_obj(
                fun, v, matches, new_path + '.', context
            )
        except Exception:
            pass

    return matches


class timeout_of(object):
    def __init__(self, time, strict=False):
        self.time = time
        try:
            # Ignoring when not active + disabling if no alarm signal (Windows)
            signal.signal(signal.SIGALRM, signal.SIG_IGN)
        except Exception:
            if strict:
                raise Exception('Not running because timeout is not available')
            self.active = False
        else:
            self.active = True

    def timeout(self, signum, frame):
        raise Exception('Timeout')

    def __enter__(self):
        if not self.active:
            return

        signal.signal(signal.SIGALRM, self.timeout)
        signal.setitimer(signal.ITIMER_REAL, self.time)

    def __exit__(self, *args):
        if not self.active:
            return

        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, signal.SIG_IGN)


class IterableEllipsis(object):
    def __init__(self, size):
        self.size = size


def cut_if_too_long(iterable, level, tuple_=False):
    max_ = 100
    for i in range(1, min(level, 4)):
        max_ /= 2
    start = 10
    end = 5
    max_ = max(start + end, int(max_))
    size = len(iterable)
    if size > max_:
        ie = IterableEllipsis(size - start - end)
        if tuple_:
            ie = (ie, ie)
        return list(iterable[:start]) + [ie] + list(iterable[-end:])
    else:
        return iterable


# Got from:
# http://www.zopatista.com/python/2013/11/26/inplace-file-rewriting/
# as suggested by https://github.com/leorochael
@contextmanager
def inplace(
    filename,
    mode='r',
    buffering=-1,
    encoding=None,
    errors=None,
    newline=None,
    backup_extension=None,
):
    """Allow for a file to be replaced with new content.

    yields a tuple of (readable, writable) file objects, where writable
    replaces readable.

    If an exception occurs, the old file is restored, removing the
    written data.

    mode should *not* use 'w', 'a' or '+'; only read-only-modes are supported.

    """

    # move existing file to backup, create new file with same permissions
    # borrowed extensively from the fileinput module
    if set(mode).intersection('wa+'):
        raise ValueError('Only read-only file modes can be used')

    backupfilename = filename + (backup_extension or os.extsep + 'bak')
    try:
        os.unlink(backupfilename)
    except os.error:
        pass
    os.rename(filename, backupfilename)
    readable = io.open(
        backupfilename,
        mode,
        buffering=buffering,
        encoding=encoding,
        errors=errors,
        newline=newline,
    )
    try:
        perm = os.fstat(readable.fileno()).st_mode
    except OSError:
        writable = io.open(
            filename,
            'w' + mode.replace('r', ''),
            buffering=buffering,
            encoding=encoding,
            errors=errors,
            newline=newline,
        )
    else:
        os_mode = os.O_CREAT | os.O_WRONLY | os.O_TRUNC
        if hasattr(os, 'O_BINARY'):
            os_mode |= os.O_BINARY
        fd = os.open(filename, os_mode, perm)
        writable = io.open(
            fd,
            "w" + mode.replace('r', ''),
            buffering=buffering,
            encoding=encoding,
            errors=errors,
            newline=newline,
        )
        try:
            if hasattr(os, 'chmod'):
                os.chmod(filename, perm)
        except OSError:
            pass
    try:
        yield readable, writable
    except Exception:
        # move backup back
        try:
            os.unlink(filename)
        except os.error:
            pass
        os.rename(backupfilename, filename)
        raise
    finally:
        readable.close()
        writable.close()
        try:
            os.unlink(backupfilename)
        except os.error:
            pass
