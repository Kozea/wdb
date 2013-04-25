import sys
import os
from bdb import BdbQuit
from wdb import Wdb


def main():
    """Inspired by python -m pdb. Debug any python script with wdb"""
    if not sys.argv[1:] or sys.argv[1] in ("--help", "-h"):
        print "usage: wdb.py scriptfile [arg] ..."
        sys.exit(2)

    mainpyfile = sys.argv[1]
    if not os.path.exists(mainpyfile):
        print 'Error:', mainpyfile, 'does not exist'
        sys.exit(1)

    del sys.argv[0]
    sys.path[0] = os.path.dirname(mainpyfile)

    # Let's make a server in case of
    wdbr = Wdb.make_server()

    # Prepare full tracing
    frame = sys._getframe()
    while frame:
        frame.f_trace = wdbr.trace_dispatch
        wdbr.botframe = frame
        frame = frame.f_back
    wdbr.stopframe = sys._getframe().f_back
    wdbr.stoplineno = -1

    # Init the python context
    import __main__
    __main__.__dict__.clear()
    __main__.__dict__.update({
        "__name__": "__main__",
        "__file__": mainpyfile,
        "__builtins__": __builtins__,
    })
    cmd = 'execfile(%r)\n' % mainpyfile

    # Set trace with wdb
    sys.settrace(wdbr.trace_dispatch)
    try:
        exec cmd in __main__.__dict__, __main__.__dict__
    except BdbQuit:
        pass
    finally:
        wdbr.quitting = 1
        sys.settrace(None)


if __name__ == '__main__':
    main()
