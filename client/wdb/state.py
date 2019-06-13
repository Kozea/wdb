from .utils import pretty_frame


class State(object):
    def __init__(self, frame):
        self.frame = frame

    def up(self):
        """Go up in stack and return True if top frame"""
        if self.frame:
            self.frame = self.frame.f_back
            return self.frame is None

    def __repr__(self):
        return '<State is %s for %s>' % (
            self.__class__.__name__,
            pretty_frame(self.frame),
        )


class Running(State):
    """Running state: never stopping"""

    def stops(self, frame, event):
        return False


class Step(State):
    """Stepping state: always stopping"""

    def stops(self, frame, event):
        return True


class Next(State):
    """Nexting state: stop if same frame"""

    def stops(self, frame, event):
        return self.frame == frame


class Until(State):
    """Nexting until state: stop if same frame and is next line"""

    def __init__(self, frame, lno):
        self.frame = frame
        self.lno = lno + 1

    def stops(self, frame, event):
        return self.frame == frame and frame.f_lineno >= self.lno


class Return(Next):
    """Returning state: Stop on return event if same frame"""

    def stops(self, frame, event):
        return self.frame == frame and event == 'return'
