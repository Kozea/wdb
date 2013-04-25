import sys
import os
from wdb import WdbRequest, AltServer
from random import randint


def main():
    if not sys.argv[1:] or sys.argv[1] in ("--help", "-h"):
        print "usage: wdb.py scriptfile [arg] ..."
        sys.exit(2)

    mainpyfile = sys.argv[1]
    if not os.path.exists(mainpyfile):
        print 'Error:', mainpyfile, 'does not exist'
        sys.exit(1)

    del sys.argv[0]
    sys.path[0] = os.path.dirname(mainpyfile)

    rand_ports = [randint(10000, 60000) for _ in range(5)]
    AltServer(rand_ports)
    self = WdbRequest(rand_ports)

    self.quitting = 0
    self.begun = False
    self.reset()

    frame = sys._getframe()
    while frame:
        frame.f_trace = self.trace_dispatch
        self.botframe = frame
        frame = frame.f_back
    self.stopframe = sys._getframe().f_back
    self.stoplineno = -1
    sys.settrace(self.trace_dispatch)
    import __main__
    __main__.__dict__.clear()
    __main__.__dict__.update({
        "__name__": "__main__",
        "__file__": mainpyfile,
        "__builtins__": __builtins__,
    })
    self._wait_for_mainpyfile = 1
    self.mainpyfile = self.canonic(mainpyfile)
    statement = 'execfile(%r)' % mainpyfile
    self.run(statement)


if __name__ == '__main__':
    main()
