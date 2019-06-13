# *-* coding: utf-8 *-*
import os
import re
import sys
import time
import token as tokens
import traceback
from base64 import b64encode
from logging import WARNING
from subprocess import Popen
from tokenize import TokenError, generate_tokens

from . import __version__, _initial_globals
from ._compat import (
    JSONEncoder,
    StringIO,
    _detect_lines_encoding,
    dumps,
    escape,
    execute,
    force_bytes,
    from_bytes,
    is_str,
    loads,
    logger,
    quote,
    u,
)
from .utils import (
    Html5Diff,
    executable_line,
    get_doc,
    get_source,
    importable_module,
    inplace,
    search_key_in_obj,
    search_value_in_obj,
    timeout_of,
)

try:
    from cutter import cut
    from cutter.utils import bang_compile as compile
except ImportError:
    cut = None

try:
    import magic
except ImportError:
    magic = None

try:
    from jedi import Interpreter
except ImportError:
    Interpreter = None

log = logger('wdb.ui')


def eval_(src, *args, **kwargs):
    return eval(compile(src, '<stdin>', 'eval'), *args, **kwargs)


class ReprEncoder(JSONEncoder):
    """JSON encoder using repr for objects"""

    def default(self, obj):
        return repr(obj)


def dump(o):
    """Shortcut to json.dumps with ReprEncoder"""
    return dumps(o, cls=ReprEncoder, sort_keys=True)


def tokenize_redir(raw_data):
    raw_io = StringIO()
    raw_io.write(raw_data)
    raw_io.seek(0)
    last_token = ''

    for token_type, token, src, erc, line in generate_tokens(raw_io.readline):
        if (
            token_type == tokens.ERRORTOKEN
            and token == '!'
            and last_token in ('>', '>>')
        ):
            return (
                line[: src[1] - 1],
                line[erc[1] :].lstrip(),
                last_token == '>>',
            )
        last_token = token
    return


class Interaction(object):

    hooks = {
        'update_watchers': [
            'start',
            'eval',
            'watch',
            'init',
            'select',
            'unwatch',
        ]
    }

    def __init__(
        self,
        db,
        frame,
        tb,
        exception,
        exception_description,
        init=None,
        shell=False,
        shell_vars=None,
        source=None,
        timeout=None,
    ):
        self.db = db
        self.shell = shell
        self.init_message = init
        self.stack, self.trace, self.index = self.db.get_trace(frame, tb)
        self.exception = exception
        self.exception_description = exception_description
        # Copy locals to avoid strange cpython behaviour
        self.locals = list(map(lambda x: x[0].f_locals, self.stack))
        self.htmldiff = Html5Diff(4)
        self.timeout = timeout

        if self.shell:
            self.locals[self.index] = shell_vars or {}

        if source:
            with open(source) as f:
                compiled_code = compile(f.read(), '<source>', 'exec')
            # Executing in locals to keep local scope
            # (http://bugs.python.org/issue16781)
            execute(compiled_code, self.current_locals, self.current_locals)

    def hook(self, kind):
        for hook, events in self.hooks.items():
            if kind in events:
                getattr(self, hook)()

    @property
    def current(self):
        return self.trace[self.index]

    @property
    def current_frame(self):
        return self.stack[self.index][0]

    @property
    def current_locals(self):
        return self.locals[self.index]

    @property
    def current_file(self):
        return self.current['file']

    def get_globals(self):
        """Get enriched globals"""
        if self.shell:
            globals_ = dict(_initial_globals)
        else:
            globals_ = dict(self.current_frame.f_globals)
        globals_['_'] = self.db.last_obj
        if cut is not None:
            globals_.setdefault('cut', cut)
        # For meta debuging purpose
        globals_['___wdb'] = self.db
        # Hack for function scope eval
        globals_.update(self.current_locals)
        for var, val in self.db.extra_vars.items():
            globals_[var] = val
        self.db.extra_items = {}
        return globals_

    def init(self):
        self.db.send(
            'Title|%s'
            % dump(
                {
                    'title': self.exception,
                    'subtitle': self.exception_description,
                }
            )
        )
        if self.shell:
            self.db.send('Shell')
        else:
            self.db.send(
                'Trace|%s' % dump({'trace': self.trace, 'cwd': os.getcwd()})
            )
            self.db.send(
                'SelectCheck|%s'
                % dump({'frame': self.current, 'name': self.current_file})
            )
        if self.init_message:
            self.db.send(self.init_message)
            self.init_message = None
        self.hook('init')

    def parse_command(self, message):
        # Parse received message
        if '|' in message:
            return message.split('|', 1)
        return message, ''

    def loop(self):
        stop = False
        while not stop:
            self.db.send('UPDATE_FILENAME|%s' % self.current_file)
            try:
                stop = self.interact()
            except Exception:
                log.exception('Error in loop')
                try:
                    exc = self.handle_exc()
                    type_, value = sys.exc_info()[:2]
                    link = (
                        '<a href="https://github.com/Kozea/wdb/issues/new?'
                        'title=%s&body=%s&labels=defect" class="nogood">'
                        'Please click here to report it on Github</a>'
                    ) % (
                        quote('%s: %s' % (type_.__name__, str(value))),
                        quote('```\n%s\n```\n' % traceback.format_exc()),
                    )
                    self.db.send(
                        'Echo|%s'
                        % dump(
                            {
                                'for': 'Error in Wdb, this is bad',
                                'val': exc + '<br>' + link,
                            }
                        )
                    )
                except Exception:
                    log.exception('Error in loop exception handling')
                    self.db.send(
                        'Echo|%s'
                        % dump(
                            {
                                'for': 'Too many errors',
                                'val': (
                                    "Don't really know what to say. "
                                    "Maybe it will work tomorrow."
                                ),
                            }
                        )
                    )

    def interact(self):
        try:
            message = self.db.receive(self.timeout)
            # Only timeout at first request
            self.timeout = None
        except KeyboardInterrupt:
            # Quit on KeyboardInterrupt
            message = 'Quit'

        cmd, data = self.parse_command(message)
        cmd = cmd.lower()
        log.debug('Cmd %s #Data %d' % (cmd, len(data)))
        fun = getattr(self, 'do_' + cmd, None)
        if fun:
            rv = fun(data)
            self.hook(cmd)
            return rv

        log.warning('Unknown command %s' % cmd)

    def update_watchers(self):
        watched = {}
        for watcher in self.db.watchers[self.current_file]:
            try:
                watched[watcher] = self.db.safe_better_repr(
                    eval_(watcher, self.get_globals(), self.current_locals)
                )
            except Exception as e:
                watched[watcher] = type(e).__name__

        self.db.send('Watched|%s' % dump(watched))

    def notify_exc(self, msg):
        log.info(msg, exc_info=True)
        self.db.send(
            'Log|%s'
            % dump({'message': '%s\n%s' % (msg, traceback.format_exc())})
        )

    def do_start(self, data):
        self.started = True
        # Getting breakpoints
        log.debug('Getting breakpoints')

        self.db.send(
            'Init|%s'
            % dump(
                {
                    'cwd': os.getcwd(),
                    'version': __version__,
                    'breaks': self.db.breakpoints_to_json(),
                }
            )
        )
        self.db.send(
            'Title|%s'
            % dump(
                {
                    'title': self.exception,
                    'subtitle': self.exception_description,
                }
            )
        )
        if self.shell:
            self.db.send('Shell')
        else:
            self.db.send('Trace|%s' % dump({'trace': self.trace}))

            # In case of exception always be at top frame to start
            self.index = len(self.stack) - 1
            self.db.send(
                'SelectCheck|%s'
                % dump({'frame': self.current, 'name': self.current_file})
            )

        if self.init_message:
            self.db.send(self.init_message)
            self.init_message = None

    def do_select(self, data):
        self.index = int(data)
        self.db.send(
            'SelectCheck|%s'
            % dump({'frame': self.current, 'name': self.current_file})
        )

    def do_file(self, data):
        fn = data
        file = self.db.get_file(fn)
        self.db.send(
            'Select|%s'
            % dump({'frame': self.current, 'name': fn, 'file': file})
        )

    def do_inspect(self, data):
        if '/' in data:
            mode, data = data.split('/', 1)
        else:
            mode = 'inspect'

        try:
            thing = self.db.obj_cache.get(int(data))
        except Exception:
            self.fail('Inspect')
            return
        if mode == 'dump':
            self.db.send(
                'Print|%s'
                % dump(
                    {
                        'for': self.db.safe_better_repr(thing, html=False),
                        'result': self.db.safe_better_repr(thing, full=True),
                    }
                )
            )
            return

        if isinstance(thing, tuple) and len(thing) == 3:
            type_, value, tb = thing
            iter_tb = tb
            while iter_tb.tb_next is not None:
                iter_tb = iter_tb.tb_next

            self.db.extra_vars['__recursive_exception__'] = value

            self.db.interaction(
                iter_tb.tb_frame, tb, type_.__name__, str(value)
            )
            return

        self.db.send(
            'Dump|%s'
            % dump(
                {
                    'for': self.db.safe_repr(thing),
                    'val': self.db.dmp(thing),
                    'doc': get_doc(thing),
                    'source': get_source(thing),
                }
            )
        )

    def do_dump(self, data):
        try:
            thing = eval_(data, self.get_globals(), self.current_locals)
        except Exception:
            self.fail('Dump')
            return

        self.db.send(
            'Dump|%s'
            % dump(
                {
                    'for': u('%s ⟶ %s ') % (data, self.db.safe_repr(thing)),
                    'val': self.db.dmp(thing),
                    'doc': get_doc(thing),
                    'source': get_source(thing),
                }
            )
        )

    def do_trace(self, data):
        self.db.send('Trace|%s' % dump({'trace': self.trace}))

    def do_eval(self, data):
        redir = None
        imports = []
        raw_data = data.strip()
        if raw_data.startswith('!<'):
            filename = raw_data[2:].strip()
            try:
                with open(filename, 'r') as f:
                    raw_data = f.read()
            except Exception:
                self.fail('Eval', 'Unable to read from file %s' % filename)
                return

        lines = raw_data.split('\n')
        if '>!' in lines[-1]:
            try:
                last_line, redir, append = tokenize_redir(raw_data)
            except TokenError:
                last_line = redir = None
                append = False
            if redir and last_line:
                indent = len(lines[-1]) - len(lines[-1].lstrip())
                lines[-1] = indent * u(' ') + last_line
                raw_data = '\n'.join(lines)
        data = raw_data
        # Keep spaces
        raw_data = raw_data.replace(' ', u(' '))
        # Compensate prompt for multi line
        raw_data = raw_data.replace('\n', '\n' + u(' ' * 4))
        duration = None
        with self.db.capture_output(with_hook=redir is None) as (out, err):
            compiled_code = None
            try:
                compiled_code = compile(data, '<stdin>', 'single')
            except Exception:
                try:
                    compiled_code = compile(data, '<stdin>', 'exec')
                except Exception:
                    maybe_hook = self.handle_exc()

                # Hack from codeop
                e1 = e2 = None
                try:
                    compiled_code = compile(data + '\n', '<stdin>', 'exec')
                except Exception as e:
                    e1 = e
                try:
                    compile(data + '\n\n', '<stdin>', 'exec')
                except Exception as e:
                    e2 = e

                if not compiled_code:
                    if repr(e1) != repr(e2):
                        # Multiline not terminated
                        self.db.send('NewLine')
                        return
                    else:
                        self.db.hooked = maybe_hook

            loc = self.current_locals
            start = time.time()
            if compiled_code is not None:
                self.db.compile_cache[id(compiled_code)] = data
                try:
                    execute(compiled_code, self.get_globals(), loc)
                except NameError as e:
                    m = re.match("name '(.+)' is not defined", str(e))
                    if m:
                        name = m.groups()[0]
                        if self.db._importmagic_index:
                            scores = self.db._importmagic_index.symbol_scores(
                                name
                            )
                            for _, module, variable in scores:
                                if variable is None:
                                    imports.append('import %s' % module)
                                else:
                                    imports.append(
                                        'from %s import %s'
                                        % (module, variable)
                                    )
                        elif importable_module(name):
                            imports.append('import %s' % name)

                    self.db.hooked = self.handle_exc()
                except Exception:
                    self.db.hooked = self.handle_exc()

        duration = int((time.time() - start) * 1000 * 1000)
        if redir and not self.db.hooked:
            try:
                with open(redir, 'a' if append else 'w') as f:
                    f.write('\n'.join(out) + '\n'.join(err) + '\n')
            except Exception:
                self.fail('Eval', 'Unable to write to file %s' % redir)
                return
            self.db.send(
                'Print|%s'
                % dump(
                    {
                        'for': raw_data,
                        'result': escape(
                            '%s to file %s'
                            % ('Appended' if append else 'Written', redir)
                        ),
                    }
                )
            )
        else:
            rv = escape('\n'.join(out) + '\n'.join(err))
            try:
                dump(rv)
            except Exception:
                rv = rv.decode('ascii', 'ignore')

            if rv and self.db.hooked:
                result = self.db.hooked + '\n' + rv
            elif rv:
                result = rv
            else:
                result = self.db.hooked

            self.db.send(
                'Print|%s'
                % dump(
                    {'for': raw_data, 'result': result, 'duration': duration}
                )
            )
            if imports:
                self.db.send('Suggest|%s' % dump({'imports': imports}))

    def do_ping(self, data):
        self.db.send('Pong')

    def do_step(self, data):
        self.db.set_step(self.current_frame)
        return True

    def do_next(self, data):
        self.db.set_next(self.current_frame)
        return True

    def do_continue(self, data):
        self.db.stepping = False
        self.db.set_continue(self.current_frame)
        return True

    def do_return(self, data):
        self.db.set_return(self.current_frame)
        return True

    def do_until(self, data):
        self.db.set_until(self.current_frame)
        return True

    def do_close(self, data):
        self.db.stepping = False
        if self.db.closed is not None:
            # Ignore set_trace till end
            self.db.closed = True

        self.db.set_continue(self.current_frame)
        return True

    def do_break(self, data):
        from linecache import getline

        brk = loads(data)

        def break_fail(x):
            return self.fail(
                'Break',
                'Break on %s failed' % ('%s:%s' % (brk['fn'], brk['lno'])),
                message=x,
            )

        if not brk.get('fn'):
            break_fail('Can’t break with no current file')
            return

        if brk['lno'] is not None:
            try:
                lno = int(brk['lno'])
            except Exception:
                break_fail(
                    'Wrong breakpoint format must be '
                    '[file][:lineno][#function][,condition].'
                )
                return

            line = getline(brk['fn'], lno, self.current_frame.f_globals)
            if not line:
                for path in sys.path:
                    line = getline(
                        os.path.join(path, brk['fn']),
                        brk['lno'],
                        self.current_frame.f_globals,
                    )
                    if line:
                        break
            if not line:
                break_fail('Line does not exist')
                return

            if not executable_line(line):
                break_fail('Blank line or comment')
                return

        breakpoint = self.db.set_break(
            brk['fn'], brk['lno'], brk['temporary'], brk['cond'], brk['fun']
        )
        break_set = breakpoint.to_dict()
        break_set['temporary'] = brk['temporary']
        self.db.send('BreakSet|%s' % dump(break_set))

    def do_unbreak(self, data):
        brk = loads(data)
        lno = brk['lno'] and int(brk['lno'])
        self.db.clear_break(
            brk['fn'], lno, brk['temporary'], brk['cond'], brk['fun']
        )

        self.db.send('BreakUnset|%s' % data)

    def do_breakpoints(self, data):
        self.db.send(
            'Print|%s'
            % dump({'for': 'Breakpoints', 'result': self.db.breakpoints})
        )

    def do_watch(self, data):
        self.db.watchers[self.current_file].add(data)
        self.db.send('Ack')

    def do_unwatch(self, data):
        self.db.watchers[self.current_file].remove(data)

    def do_jump(self, data):
        lno = int(data)
        if self.index != len(self.trace) - 1:
            log.error('Must be at bottom frame')
            return

        try:
            self.current_frame.f_lineno = lno
        except ValueError:
            self.fail('Unbreak')
            return

        self.current['lno'] = lno
        self.db.send('Trace|%s' % dump({'trace': self.trace}))
        self.db.send(
            'SelectCheck|%s'
            % dump({'frame': self.current, 'name': self.current_file})
        )

    def do_complete(self, data):
        completion = loads(data)
        manual = completion.pop('manual', False)
        if manual:
            timeout = 5
        else:
            timeout = 0.1

        source = completion.pop('source')
        pos = completion.pop('pos')
        if not Interpreter:
            self.db.send('Suggest')
            return
        try:
            script = Interpreter(
                source, [self.current_locals, self.get_globals()], **completion
            )
            with timeout_of(timeout, not manual):
                completions = script.completions()
        except Exception:
            self.db.send('Suggest')
            if log.level < WARNING:
                self.notify_exc('Completion failed for %s' % data)
            return

        try:
            with timeout_of(timeout / 2, not manual):
                funs = script.call_signatures() or []
        except Exception:
            self.db.send('Suggest')
            if log.level < WARNING:
                self.notify_exc('Completion of function failed for %s' % data)
            return

        before = source[:pos]
        after = source[pos:]
        like = ''
        if len(completions):
            completion = completions[0]
            base = completion.name[
                : len(completion.name) - len(completion.complete)
            ]
            if len(base):
                like = before[-len(base) :]
                if len(like):
                    before = before[: -len(like)]
        try:
            suggest_obj = {
                'data': {'start': before, 'end': after, 'like': like},
                'params': [
                    {
                        'params': [
                            p.description.replace('\n', '') for p in fun.params
                        ],
                        'index': fun.index,
                        'module': fun.module_name,
                        'call_name': fun.name,
                    }
                    for fun in funs
                ],
                'completions': [
                    {
                        'base': comp.name[
                            : len(comp.name) - len(comp.complete)
                        ],
                        'complete': comp.complete,
                        'description': comp.description,
                    }
                    for comp in completions
                    if comp.name.endswith(comp.complete)
                ],
            }
            self.db.send('Suggest|%s' % dump(suggest_obj))
        except Exception:
            self.db.send('Suggest')
            self.notify_exc('Completion generation failed for %s' % data)

    def do_save(self, data):
        fn, src = data.split('|', 1)
        if not os.path.exists(fn):
            return
        try:
            encoding = _detect_lines_encoding(src.splitlines())
            with inplace(fn, encoding=encoding) as (_, w):
                w.write(src)
        except Exception as e:
            self.db.send(
                'Echo|%s' % dump({'for': 'Error during save', 'val': str(e)})
            )
        else:
            self.db.send(
                'Echo|%s'
                % dump({'for': 'Save succesful', 'val': 'Wrote %s' % fn})
            )

    def do_external(self, data):
        default = {'linux': 'xdg-open', 'win32': '', 'darwin': 'open'}.get(
            sys.platform, 'open'
        )
        editor = os.getenv('EDITOR', os.getenv('VISUAL', default))
        if editor:
            cmd = editor.split(' ')
        else:
            cmd = []
        try:
            Popen(cmd + [data])
        except Exception:
            self.fail('External open')

    def do_display(self, data):
        if ';' in data:
            mime, data = data.split(';', 1)
            forced = True
        else:
            mime = 'text/html'
            forced = False

        try:
            thing = eval_(data, self.get_globals(), self.current_locals)
        except Exception:
            self.fail('Display')
            return
        else:
            thing = force_bytes(thing)
            if magic and not forced:
                mime = magic.from_buffer(thing, mime=True)
            self.db.send(
                'Display|%s'
                % dump(
                    {
                        'for': u('%s (%s)') % (data, mime),
                        'val': from_bytes(b64encode(thing)),
                        'type': mime,
                    }
                )
            )

    def do_disable(self, data):
        self.db.__class__.enabled = False
        self.db.stepping = False
        self.db.stop_trace()
        self.db.die()
        return True

    def do_quit(self, data):
        self.db.stepping = False
        self.db.stop_trace()
        return True

    def do_restart(self, data):
        try:
            # Try re-execing as-is
            os.execvp(sys.argv[0], sys.argv)
        except Exception:
            # Put the python executable in front
            python = sys.executable
            os.execl(python, python, *sys.argv)

    def do_diff(self, data):
        if '?' not in data and '<>' not in data:
            self.fail(
                'Diff',
                'Diff error',
                'You must provide two expression '
                'separated by "?" or "<>" to make a diff',
            )
            return
        pretty = '?' in data
        expressions = [
            expression.strip()
            for expression in (
                data.split('?') if '?' in data else data.split('<>')
            )
        ]
        strings = []
        for expression in expressions:
            try:
                strings.append(
                    eval_(expression, self.get_globals(), self.current_locals)
                )
            except Exception:
                self.fail(
                    'Diff',
                    "Diff failed: Expression %s "
                    "failed to evaluate to a string" % expression,
                )
                return

        render = (
            (
                (
                    lambda x: self.db.better_repr(x, html=False)
                    or self.db.safe_repr(x)
                )
            )
            if pretty
            else str
        )
        strings = [
            render(string) if not is_str(string) else string
            for string in strings
        ]
        self.db.send(
            'RawHTML|%s'
            % dump(
                {
                    'for': u('Difference between %s')
                    % (' and '.join(expressions)),
                    'val': self.htmldiff.make_table(
                        strings[0].splitlines(keepends=True),
                        strings[1].splitlines(keepends=True),
                        expressions[0],
                        expressions[1],
                    ),
                }
            )
        )

    def do_find(self, data):
        if ' in ' not in data and ' of ' not in data:
            self.fail(
                'Find',
                'Find error',
                'Syntax for find is: "key in expression" '
                'or "value testing function of expression"',
            )
        if ' in ' in data:
            key, expr = data.split(' in ')
        else:
            key, expr = data.split(' of ')

        try:
            value = eval_(expr, self.get_globals(), self.current_locals)
        except Exception:
            self.fail('Find')
            return
        if ' in ' in data:
            matches = search_key_in_obj(key, value, path='%s.' % expr)
        else:
            matches = search_value_in_obj(key, value, path='%s.' % expr)

        self.db.send(
            'Print|%s'
            % dump(
                {
                    'for': 'Finding %s in %s' % (key, expr),
                    'result': 'Found:\n%s'
                    % '\n'.join(
                        [
                            '%s: -> %s' % (k, escape(self.db.safe_repr(val)))
                            for k, val in matches
                        ]
                    )
                    if matches
                    else 'Not found',
                }
            )
        )

    def handle_exc(self):
        """Return a formated exception traceback for wdb.js use"""
        exc_info = sys.exc_info()
        type_, value = exc_info[:2]
        self.db.obj_cache[id(exc_info)] = exc_info

        return '<a href="%d" class="inspect">%s: %s</a>' % (
            id(exc_info),
            escape(type_.__name__),
            escape(repr(value)),
        )

    def fail(self, cmd, title=None, message=None):
        """Send back captured exceptions"""
        if message is None:
            message = self.handle_exc()
        else:
            message = escape(message)
        self.db.send(
            'Echo|%s'
            % dump({'for': escape(title or '%s failed' % cmd), 'val': message})
        )
