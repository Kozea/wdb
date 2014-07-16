# *-* coding: utf-8 *-*
from ._compat import (
    loads, dumps, JSONEncoder, quote, execute, to_unicode, u, StringIO, escape,
    to_unicode_string, from_bytes, force_bytes)
from .utils import get_source, get_doc, executable_line
from . import __version__
from tokenize import generate_tokens, TokenError
import token as tokens
from jedi import Script
from logging import getLogger
from shutil import move
from tempfile import gettempdir
from base64 import b64encode

try:
    from cutter import cut
    from cutter.utils import bang_compile as compile
except ImportError:
    cut = None

try:
    import magic
except ImportError:
    magic = None

import os
import re
import sys
import time
import pkgutil
import traceback
log = getLogger('wdb.ui')


class ReprEncoder(JSONEncoder):
    """JSON encoder using repr for objects"""

    def default(self, obj):
        return repr(obj)


def dump(o):
    """Shortcut to json.dumps with ReprEncoder"""
    return dumps(o, cls=ReprEncoder, sort_keys=True)


def handle_exc():
    """Return a formated exception traceback for wdb.js use"""
    type_, value = sys.exc_info()[:2]
    return '<a title="%s">%s: %s</a>' % (
        escape(traceback.format_exc().replace('"', '\'')),
        escape(type_.__name__), escape(str(value)))


def fail(db, cmd, title=None, message=None):
    """Send back captured exceptions"""
    if message is None:
        message = handle_exc()
    else:
        message = escape(message)
    db.send('Echo|%s' % dump({
        'for': escape(title or '%s failed' % cmd),
        'val': message
    }))


def tokenize_redir(raw_data):
    raw_io = StringIO()
    raw_io.write(raw_data)
    raw_io.seek(0)
    last_token = ''

    for token_type, token, src, erc, line in generate_tokens(raw_io.readline):
        if (token_type == tokens.ERRORTOKEN and
                token == '!' and
                last_token in ('>', '>>')):
            return (line[:src[1] - 1],
                    line[erc[1]:].lstrip(),
                    last_token == '>>')
        last_token = token
    return


class Interaction(object):

    hooks = {
        'update_watchers': [
            'start', 'eval', 'watch', 'init', 'select', 'unwatch']
    }

    def __init__(
            self, db, frame, tb, exception, exception_description, init=None):
        self.db = db
        self.init_message = init
        self.stack, self.trace, self.index = self.db.get_trace(frame, tb)
        self.exception = exception
        self.exception_description = exception_description
        # Copy locals to avoid strange cpython behaviour
        self.locals = list(map(lambda x: x[0].f_locals, self.stack))

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
        globals_ = dict(self.current_frame.f_globals)
        globals_['_'] = self.db.last_obj
        if cut is not None:
            globals_['cut'] = cut
        # For meta debuging purpose
        globals_['___wdb'] = self.db
        # Hack for function scope eval
        globals_.update(self.current_locals)
        for var, val in self.db.extra_vars.items():
            globals_[var] = val
        self.db.extra_items = {}
        return globals_

    def init(self):
        self.db.send('Title|%s' % dump({
            'title': self.exception,
            'subtitle': self.exception_description
        }))
        self.db.send('Trace|%s' % dump({
            'trace': self.trace,
            'cwd': os.getcwd()
        }))
        self.db.send('SelectCheck|%s' % dump({
            'frame': self.current,
            'name': self.current_file
        }))
        self.hook('init')

    def parse_command(self, message):
        # Parse received message
        if '|' in message:
            return message.split('|', 1)
        return message, ''

    def loop(self):
        stop = False
        while not stop:
            try:
                stop = self.interact()
            except Exception:
                log.exception('Error in loop')
                try:
                    exc = handle_exc()
                    type_, value = sys.exc_info()[:2]
                    link = (
                        '<a href="https://github.com/Kozea/wdb/issues/new?'
                        'title=%s&body=%s&labels=defect" class="nogood">'
                        'Please click here to report it on Github</a>') % (
                        quote('%s: %s' % (type_.__name__, str(value))),
                        quote('```\n%s\n```\n' %
                              traceback.format_exc()))
                    self.db.send('Echo|%s' % dump({
                        'for': 'Error in Wdb, this is bad',
                        'val': exc + '<br>' + link
                    }))
                except Exception:
                    log.exception('Error in loop exception handling')
                    self.db.send('Echo|%s' % dump({
                        'for': 'Too many errors',
                        'val': ("Don't really know what to say. "
                                "Maybe it will work tomorrow.")
                    }))

    def interact(self):
        try:
            message = self.db.receive()
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
                watched[watcher] = self.db.safe_better_repr(eval(
                    watcher, self.get_globals(), self.locals[self.index]))
            except Exception as e:
                watched[watcher] = type(e).__name__

        self.db.send('Watched|%s' % dump(watched))

    def notify_exc(self, msg):
        log.info(msg, exc_info=True)
        self.db.send('Log|%s' % dump({
            'message': '%s\n%s' % (msg, traceback.format_exc())
        }))

    def do_start(self, data):
        # Getting breakpoints
        log.debug('Getting breakpoints')

        self.db.send('Init|%s' % dump({
            'cwd': os.getcwd(),
            'version': __version__,
            'breaks': self.db.breakpoints_to_json()
        }))
        self.db.send('Title|%s' % dump({
            'title': self.exception,
            'subtitle': self.exception_description
        }))
        self.db.send('Trace|%s' % dump({
            'trace': self.trace
        }))

        # In case of exception always be at top frame to start
        self.index = len(self.stack) - 1
        self.db.send('SelectCheck|%s' % dump({
            'frame': self.current,
            'name': self.current_file
        }))
        if self.init_message:
            self.db.send(self.init_message)
            self.init_message = None

    def do_select(self, data):
        self.index = int(data)
        self.db.send('SelectCheck|%s' % dump({
            'frame': self.current,
            'name': self.current_file
        }))

    def do_file(self, data):
        fn = data
        file = self.db.get_file(fn)
        self.db.send('Select|%s' % dump({
            'frame': self.current,
            'name': fn,
            'file': file
        }))

    def do_inspect(self, data):
        try:
            thing = self.db.obj_cache.get(int(data))
        except Exception:
            fail(self.db, 'Inspect')
            return

        self.db.send('Dump|%s' % dump({
            'for': repr(thing),
            'val': self.db.dmp(thing),
            'doc': get_doc(thing),
            'source': get_source(thing)
        }))

    def do_dump(self, data):
        try:
            thing = eval(
                data, self.get_globals(), self.locals[self.index])
        except Exception:
            fail(self.db, 'Dump')
            return

        self.db.send('Dump|%s' % dump({
            'for': u('%s ⟶ %s ') % (data, repr(thing)),
            'val': self.db.dmp(thing),
            'doc': get_doc(thing),
            'source': get_source(thing)}))

    def do_trace(self, data):
        self.db.send('Trace|%s' % dump({
            'trace': self.trace
        }))

    def do_eval(self, data):
        redir = None
        suggest = None
        raw_data = data.strip()
        if raw_data.startswith('!<'):
            filename = raw_data[2:].strip()
            try:
                with open(filename, 'r') as f:
                    raw_data = f.read()
            except Exception:
                fail(self.db, 'Eval', 'Unable to read from file %s' % filename)
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

        with self.db.capture_output(
                with_hook=redir is None) as (out, err):
            try:
                compiled_code = compile(data, '<stdin>', 'single')
                l = self.locals[self.index]
                execute(compiled_code, self.get_globals(), l)
            except NameError as e:
                m = re.match("name '(.+)' is not defined", str(e))
                if m:
                    name = m.groups()[0]
                    for loader, module, ispkg in pkgutil.iter_modules():
                        if module == name:
                            suggest = 'import %s' % module
                            break
                self.db.hooked = handle_exc()
            except Exception:
                self.db.hooked = handle_exc()

        if redir and not self.db.hooked:
            try:
                with open(redir, 'a' if append else 'w') as f:
                    f.write('\n'.join(out) + '\n'.join(err) + '\n')
            except Exception:
                fail(self.db, 'Eval', 'Unable to write to file %s' % redir)
                return
            self.db.send('Print|%s' % dump({
                'for': raw_data,
                'result': escape('%s to file %s' % (
                    'Appended' if append else 'Written', redir),)
            }))
        else:
            rv = escape('\n'.join(out) + '\n'.join(err))
            try:
                _ = dump(rv)
            except Exception:
                rv = rv.decode('ascii', 'ignore')

            if rv and self.db.last_obj is None or not self.db.hooked:
                result = rv
            elif not rv:
                result = self.db.hooked
            else:
                result = self.db.hooked + '\n' + rv

            self.db.send('Print|%s' % dump({
                'for': raw_data,
                'result': result,
                'suggest': suggest
            }))

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

    def do_break(self, data):
        from linecache import getline

        brk = loads(data)
        break_fail = lambda x: fail(
            self.db, 'Break', 'Break on %s failed' % (
                '%s:%s' % (brk['fn'], brk['lno'])), message=x)

        if brk['lno'] is not None:
            try:
                lno = int(brk['lno'])
            except Exception:
                break_fail(
                    'Wrong breakpoint format must be '
                    '[file][:lineno][#function][,condition].')
                return

            line = getline(
                brk['fn'], lno, self.current_frame.f_globals)
            if not line:
                for path in sys.path:
                    line = getline(
                        os.path.join(path, brk['fn']),
                        brk['lno'], self.current_frame.f_globals)
                    if line:
                        break
            if not line:
                break_fail('Line does not exist')
                return

            if not executable_line(line):
                break_fail('Blank line or comment')
                return

        breakpoint = self.db.set_break(
            brk['fn'], brk['lno'], brk['temporary'], brk['cond'], brk['fun'])
        break_set = breakpoint.to_dict()
        break_set['temporary'] = brk['temporary']
        self.db.send('BreakSet|%s' % dump(break_set))

    def do_unbreak(self, data):
        brk = loads(data)
        lno = brk['lno'] and int(brk['lno'])
        self.db.clear_break(
            brk['fn'], lno, brk['temporary'], brk['cond'], brk['fun'])

        self.db.send('BreakUnset|%s' % data)

    def do_breakpoints(self, data):
        self.db.send('Print|%s' % dump({
            'for': 'Breakpoints',
            'result': self.db.breakpoints
        }))

    def do_watch(self, data):
        self.db.watchers[self.current_file].append(data)
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
            fail(self.db, 'Unbreak')
            return

        self.current['lno'] = lno
        self.db.send('Trace|%s' % dump({
            'trace': self.trace
        }))
        self.db.send('SelectCheck|%s' % dump({
            'frame': self.current,
            'name': self.current_file
        }))

    def do_complete(self, data):
        file_ = self.db.get_file(self.current_file)
        file_ = to_unicode(file_)
        lines = file_.splitlines()
        lno = self.current['lno']
        line_before = ''
        if len(lines) >= lno:
            line_before = lines[lno - 1]
        indent = len(line_before) - len(line_before.lstrip())
        segments = data.splitlines()
        for segment in reversed(segments):
            line = u(' ') * indent + segment
            lines.insert(lno - 1, line)
        script = Script(
            u('\n').join(lines), lno - 1 + len(segments),
            len(segments[-1]) + indent, '')
        try:
            completions = script.completions()
        except Exception:
            self.db.send('Suggest')
            self.notify_exc('Completion failed for %s' % (
                '\n'.join(reversed(segments))))
            return

        try:
            funs = script.call_signatures() or []
        except Exception:
            self.db.send('Suggest')
            self.notify_exc('Completion of function failed for %s' % (
                '\n'.join(reversed(segments))))
            return

        try:
            suggest_obj = {
                'params': [{
                    'params': [p.get_code().replace('\n', '')
                               for p in fun.params],
                    'index': fun.index,
                    'module': fun.module.path,
                    'call_name': fun.call_name} for fun in funs],
                'completions': [{
                    'base': comp.name[
                        :len(comp.name) - len(comp.complete)],
                    'complete': comp.complete,
                    'description': comp.description
                } for comp in completions if comp.name.endswith(
                    comp.complete)]
            }
            self.db.send('Suggest|%s' % dump(suggest_obj))
        except Exception:
            self.db.send('Suggest')
            self.notify_exc('Completion generation failed for %s' % (
                '\n'.join(reversed(segments))))

    def do_save(self, data):
        fn, src = data.split('|', 1)
        if os.path.exists(fn):
            dn = os.path.dirname(fn)
            bn = os.path.basename(fn)
            try:
                move(
                    fn, os.path.join(
                        gettempdir(),
                        dn.replace(os.path.sep, '!') + bn +
                        '-wdb-back-%d' % time.time()))
                with open(fn, 'w') as f:
                    f.write(to_unicode_string(src, fn))
            except OSError as e:
                self.db.send('Echo|%s' % dump({
                    'for': 'Error during save',
                    'val': str(e)
                }))
            else:
                self.db.send('Echo|%s' % dump({
                    'for': 'Save succesful',
                    'val': 'Wrote %s' % fn
                }))

    def do_display(self, data):
        if ';' in data:
            mime, data = data.split(';', 1)
        else:
            mime = 'text/html'

        try:
            thing = eval(
                data, self.get_globals(), self.locals[self.index])
        except Exception:
            fail(self.db, 'Display')
            return
        else:
            thing = force_bytes(thing)
            if magic:
                with magic.Magic(flags=magic.MAGIC_MIME_TYPE) as m:
                    mime = m.id_buffer(thing)
            self.db.send('Display|%s' % dump({
                'for': u('%s (%s)') % (data, mime),
                'val': from_bytes(b64encode(thing)),
                'type': mime}))

    def do_disable(self, data):
        self.db.__class__.enabled = False
        self.db.stepping = False
        self.db.stop_trace()
        self.db.die()
        return True

    def do_quit(self, data):
        self.db.stepping = False
        self.db.stop_trace()
        sys.exit(1)
