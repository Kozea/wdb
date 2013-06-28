# *-* coding: utf-8 *-*
from ._compat import dumps, JSONEncoder, quote, execute, to_unicode, u
from bdb import BdbQuit
from cgi import escape
from jedi import Script
from linecache import getline
from log_colorizer import get_color_logger
from shutil import move
from tempfile import gettempdir
import os
import sys
import time
import traceback
log = get_color_logger('wdb.ui')


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


class Interaction(object):
    def __init__(
            self, db, frame, tb, exception, exception_description, init=None):
        self.db = db
        self.init_message = init
        self.stack, self.trace, self.index = self.db.get_trace(frame, tb)
        self.exception = exception
        self.exception_description = exception_description
        # Copy locals to avoid strange cpython behaviour
        self.locals = list(map(lambda x: x[0].f_locals, self.stack))

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
            'breaks': self.db.get_breaks_lno(self.current_file),
            'name': self.current_file
        }))

    def parse_command(self, message):
        # Parse received message
        if '|' in message:
            pipe = message.index('|')
            return message[:pipe], message[pipe + 1:]
        return message, ''

    def loop(self):
        stop = False
        while not stop:
            try:
                stop = self.interact()
            except BdbQuit:
                # This will be handled by caller
                raise
            # except WsError:
            #     stop = True
            except Exception:
                log.exception('Error in loop')
                try:
                    exc = handle_exc()
                    type_, value = sys.exc_info()[:2]
                    link = ('<a href="https://github.com/Kozea/wdb/issues/new?'
                            'title=%s&body=%s&labels=defect" class="nogood">'
                            'Please click here to report it on Github</a>') % (
                                quote('%s: %s' % (type_.__name__, str(value))),
                                quote('```\n%s\n```\n' %
                                      traceback.format_exc()))
                    self.db.send('Echo|%s' % dump({
                        'for': 'Error in Wdb, this is bad',
                        'val': exc + '<br>' + link
                    }))
                except:
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
        log.debug('Cmd %s #Data %d' % (cmd, len(data)))
        fun = getattr(self, 'do_' + cmd.lower(), None)
        if fun:
            return fun(data)

        log.warn('Unknown command %s' % cmd)

    def do_start(self, data):
        self.db.send('Init|%s' % dump({
            'cwd': os.getcwd()
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
            'breaks': self.db.get_breaks_lno(self.current_file),
            'name': self.current_file
        }))
        if self.init_message:
            self.db.send(self.init_message)
            self.init_message = None

    def do_select(self, data):
        self.index = int(data)
        self.db.send('SelectCheck|%s' % dump({
            'frame': self.current,
            'breaks': self.db.get_breaks_lno(self.current_file),
            'name': self.current_file
        }))

    def do_file(self, data):
        fn = data
        file = self.db.get_file(fn)
        self.db.send('Select|%s' % dump({
            'frame': self.current,
            'breaks': self.db.get_breaks_lno(fn),
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
            'val': self.db.dmp(thing)}))

    def do_dump(self, data):
        try:
            thing = eval(
                data, self.get_globals(), self.locals[self.index])
        except Exception:
            fail(self.db, 'Dump')
            return
        else:
            self.db.send('Dump|%s' % dump({
                'for': u('%s ⟶ %s ') % (data, repr(thing)),
                'val': self.db.dmp(thing)}))

    def do_trace(self, data):
        self.db.send('Trace|%s' % dump({
            'trace': self.trace
        }))

    def do_eval(self, data):
        redir = None
        raw_data = data = data.strip()
        # Keep spaces
        raw_data = raw_data.replace(' ', u(' '))
        # Compensate prompt for multi line
        raw_data = raw_data.replace('\n', '\n' + u(' ' * 4))
        if '!>' in data:
            data, redir = data.split('!>')
            data = data.strip()
            redir = redir.strip()
        elif data.startswith('!<'):
            filename = data[2:].strip()
            try:
                with open(filename, 'r') as f:
                    data = f.read()
            except Exception:
                fail(self.db, 'Eval', 'Unable to read from file %s' % filename)
                return

        with self.db.capture_output(
                with_hook=redir is None) as (out, err):
            try:
                compiled_code = compile(data, '<stdin>', 'single')
                l = self.locals[self.index]
                execute(compiled_code, self.get_globals(), l)
            except Exception:
                self.db.hooked = handle_exc()
        if redir:
            try:
                with open(redir, 'w') as f:
                    f.write('\n'.join(out) + '\n'.join(err) + '\n')
            except Exception:
                fail(self.db, 'Eval', 'Unable to write to file %s' % redir)
                return
            self.db.send('Print|%s' % dump({
                'for': raw_data,
                'result': escape('Written to file %s' % redir)
            }))
        else:
            self.db.send('Print|%s' % dump({
                'for': raw_data,
                'result': self.db.hooked + escape(
                    '\n'.join(out) + '\n'.join(err))
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

    def do_break(self, data, temporary=False):
        break_fail = lambda x: fail(
            self.db, 'Break', 'Break on %s failed' % data, message=x)

        lno = cond = funcname = None
        remaining = data

        if ',' in data:
            remaining, cond = remaining.split(',')
            cond = cond.strip()

        if '#' in data:
            remaining, funcname = remaining.split('#')

        if ':' in data:
            remaining, lno = remaining.split(':')

        fn = remaining or self.current_file

        if lno is not None:
            try:
                lno = int(lno)
            except:
                break_fail(
                    'Wrong breakpoint format must be '
                    '[file][:lineno][#function][,condition].')
                return

            line = getline(
                fn, lno, self.current_frame.f_globals)
            if not line:
                for path in sys.path:
                    line = getline(
                        os.path.join(path, fn),
                        lno, self.current_frame.f_globals)
                    if line:
                        break
            if not line:
                break_fail('Line does not exist')
                return

            line = line.strip()
            if ((not line or (line[0] == '#') or
                 (line[:3] == '"""') or
                 line[:3] == "'''")):
                break_fail('Blank line or comment')
                return

        self.db.set_break(
            fn, lno, temporary, cond, funcname)

        if fn == self.current_file:
            self.db.send('BreakSet|%s' % dump({
                'lno': lno, 'cond': cond, 'temporary': temporary
            }))
        else:
            self.db.send('BreakSet|%s' % dump({
                'temporary': temporary
            }))

    def do_tbreak(self, data):
        return self.do_break(data, True)

    def do_unbreak(self, data):
        lno = int(data)
        log.info('Break unset at %s:%d' % (self.current_file, lno))
        self.db.clear_break(self.current_file, lno)
        self.db.send('BreakUnset|%s' % dump({'lno': lno}))

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
            'breaks': self.db.get_breaks_lno(self.current_file),
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
            completions = script.complete()
        except:
            log.info('Completion failed', exc_info=True)
            self.db.send('Log|%s' % dump({
                'message': 'Completion failed for %s' %
                '\n'.join(reversed(segments))
            }))
        else:
            fun = script.get_in_function_call()
            self.db.send('Suggest|%s' % dump({
                'params': {
                    'params': [p.get_code().replace('\n', '')
                               for p in fun.params],
                    'index': fun.index,
                    'module': fun.module.path,
                    'call_name': fun.call_name} if fun else None,
                'completions': [{
                    'base': comp.word[
                        :len(comp.word) - len(comp.complete)],
                    'complete': comp.complete,
                    'description': comp.description
                } for comp in completions if comp.word.endswith(
                    comp.complete)]
            }))

    def do_save(self, data):
        pipe = data.index('|')
        fn = data[:pipe]
        src = data[pipe + 1:]
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
                    f.write(src.encode('utf-8'))
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
