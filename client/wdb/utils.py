import inspect
import dis
import sys
from difflib import HtmlDiff, _mdiff
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
        text = (text.replace("&", "&amp;")
                .replace(">", "&gt;").replace("<", "&lt;"))

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

        return ('<td class="diff_lno"%s>%s</td>'
                '<td class="diff_line diff_line_%s">%s</td>' % (
                    id, linenum, type_, text))

    def make_table(self, fromlines, tolines, fromdesc='', todesc='',
                   context=False, numlines=5):
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
                charjunk=self._charjunk)

        # set up iterator to wrap lines that exceed desired width
        if self._wrapcolumn:
            diffs = self._line_wrapper(diffs)

        # collect up from/to lines and flags into lists (also format the lines)
        fromlist, tolist, flaglist = self._collect_lines(diffs)

        # process change flags, generating middle column of next anchors/links
        fromlist, tolist, flaglist, next_href, next_id = self._convert_flags(
            fromlist, tolist, flaglist, context, numlines)

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
                '<th colspan="2" class="diff_header">%s</th>' % todesc)
        else:
            header_row = ''

        table = self._table_template % dict(
            data_rows=''.join(s),
            header_row=header_row,
            prefix=self._prefix[1])

        return (table
                .replace('\0+', '<span class="diff_add">').
                replace('\0-', '<span class="diff_sub">').
                replace('\0^', '<span class="diff_chg">').
                replace('\1', '</span>').
                replace('\t', '&nbsp;'))
