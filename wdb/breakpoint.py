import os.path
from log_colorizer import get_color_logger

log = get_color_logger('wdb.bp')


def canonic(filename):
    if filename == "<" + filename[1:-1] + ">":
        return filename
    canonic = os.path.abspath(filename)
    canonic = os.path.normcase(canonic)
    return canonic


class Breakpoint(object):
    """Simple breakpoint that breaks if in file"""

    def __init__(self, file, temporary=False):
        self.file = canonic(file)
        self.temporary = temporary

    def on_file(self, filename):
        return canonic(filename) == self.file

    def breaks(self, frame):
        return self.on_file(frame.f_code.co_filename)


class LineBreakpoint(Breakpoint):
    """Simple breakpoint that breaks if in file at line"""
    def __init__(self, file, line, temporary=False):
        self.line = line
        super(LineBreakpoint, self).__init__(file, temporary)

    def breaks(self, frame):
        return (super(LineBreakpoint, self).breaks(frame) and
                frame.f_lineno == self.line)


class ConditionalBreakpoint(LineBreakpoint):
    """Breakpoint that breaks if condition is True at line in file"""
    def __init__(self, file, line, condition, temporary=False):
        self.condition = condition
        super(ConditionalBreakpoint, self).__init__(file, line, temporary)

    def breaks(self, frame):
        try:
            return (super(ConditionalBreakpoint, self).breaks(frame) and
                    eval(self.condition, frame.f_globals, frame.f_locals))
        except:
            # Break in case of
            return True


class FunctionBreakpoint(Breakpoint):
    """Breakpoint that breaks if in file in function"""
    def __init__(self, file, function, temporary=False):
        self.function = function
        super(FunctionBreakpoint, self).__init__(file, temporary)

    def breaks(self, frame):
        return (super(LineBreakpoint, self).breaks(frame) and
                frame.f_code.co_name == self.function)
