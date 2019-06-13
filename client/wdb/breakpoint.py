import os.path
from hashlib import sha1
from ._compat import import_module, logger

log = logger('wdb.bp')


def canonic(filename):
    if filename == "<" + filename[1:-1] + ">":
        return filename
    canonic = os.path.abspath(filename)
    canonic = os.path.normcase(canonic)
    if canonic.endswith(('.pyc', '.pyo')):
        canonic = canonic[:-1]
    return canonic


def file_from_import(filename, function=None):
    try:
        module = import_module(filename)
    except ImportError:
        return filename
    if function is None:
        return module.__file__
    fun = getattr(module, function, None)
    if not fun or not hasattr(fun, '__code__'):
        return filename
    return fun.__code__.co_filename


class Breakpoint(object):
    """Simple breakpoint that breaks if in file"""

    def __init__(self, file, temporary=False):
        self.fn = file
        if not file.endswith(('.py', '.pyc', '.pyo')):
            file = file_from_import(file)
        self.file = canonic(file)
        self.temporary = temporary

    def on_file(self, filename):
        return canonic(filename) == self.file

    def breaks(self, frame):
        return self.on_file(frame.f_code.co_filename)

    def __repr__(self):
        s = 'Temporary ' if self.temporary else ''
        s += self.__class__.__name__
        s += ' on file %s' % self.file
        return s

    def __eq__(self, other):
        return self.file == other.file and self.temporary == other.temporary

    def __hash__(self):
        s = sha1()
        s.update(repr(self).encode('utf-8'))
        return int(s.hexdigest(), 16)

    def to_dict(self):
        return {
            'fn': self.file,
            'lno': getattr(self, 'line', None),
            'cond': getattr(self, 'condition', None),
            'fun': getattr(self, 'function', None),
            'temporary': self.temporary,
        }


class LineBreakpoint(Breakpoint):
    """Simple breakpoint that breaks if in file at line"""

    def __init__(self, file, line, temporary=False):
        self.line = line
        super(LineBreakpoint, self).__init__(file, temporary)

    def breaks(self, frame):
        return (
            super(LineBreakpoint, self).breaks(frame)
            and frame.f_lineno == self.line
        )

    def __repr__(self):
        return (
            super(LineBreakpoint, self).__repr__() + ' on line %d' % self.line
        )

    def __eq__(self, other):
        return (
            super(LineBreakpoint, self).__eq__(other)
            and self.line == other.line
        )

    def __hash__(self):
        return super(LineBreakpoint, self).__hash__()


class ConditionalBreakpoint(Breakpoint):
    """Breakpoint that breaks if condition is True at line in file"""

    def __init__(self, file, line, condition, temporary=False):
        self.line = line
        self.condition = condition
        super(ConditionalBreakpoint, self).__init__(file, temporary)

    def breaks(self, frame):
        try:
            return (
                super(ConditionalBreakpoint, self).breaks(frame)
                and (self.line is None or frame.f_lineno == self.line)
                and eval(self.condition, frame.f_globals, frame.f_locals)
            )
        except Exception:
            # Break in case of
            log.warning('Error in conditional break', exc_info=True)
            return True

    def __repr__(self):
        return (
            super(ConditionalBreakpoint, self).__repr__()
            + ' under the condition %s' % self.condition
        )

    def __eq__(self, other):
        return (
            super(ConditionalBreakpoint, self).__eq__(other)
            and self.condition == other.condition
        )

    def __hash__(self):
        return super(ConditionalBreakpoint, self).__hash__()


class FunctionBreakpoint(Breakpoint):
    """Breakpoint that breaks if in file in function"""

    def __init__(self, file, function, temporary=False):
        self.function = function
        if not file.endswith(('.py', '.pyc', '.pyo')):
            file = file_from_import(file, function)
        self.file = canonic(file)
        self.temporary = temporary

    def breaks(self, frame):
        return (
            super(FunctionBreakpoint, self).breaks(frame)
            and frame.f_code.co_name == self.function
        )

    def __repr__(self):
        return (
            super(FunctionBreakpoint, self).__repr__()
            + ' in function %s' % self.function
        )

    def __eq__(self, other):
        return (
            super(FunctionBreakpoint, self).__eq__(other)
            and self.function == other.function
        )

    def __hash__(self):
        return super(FunctionBreakpoint, self).__hash__()
