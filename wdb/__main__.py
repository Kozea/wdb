import sys
import multiprocessing
import threading
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

    # Multithread support
    # Monkey patch threading to have callback to kill thread debugger
    old_thread_start = threading.Thread.start

    def wdb_thread_start(self):
        """Monkey patched start monkey patching run"""
        self.old_run = self.run

        def run(self):
            """Monkey patched run"""
            try:
                self.old_run()
            finally:
                if hasattr(self, '_wdbr'):
                    self._wdbr.die()
        import types
        self.run = types.MethodType(run, self, self.__class__)
        old_thread_start(self)
    threading.Thread.start = wdb_thread_start

    def init_new_wdbr(frame, event, args):
        """First settrace call start the debugger for the current thread"""
        thread = threading.currentThread()
        if getattr(thread, 'no_trace', False):
            sys.settrace(None)
            return None

        wdbr_thread = Wdb.make_server()
        thread._wdbr = wdbr_thread

        frame = sys._getframe()
        while frame:
            frame.f_trace = wdbr_thread.trace_dispatch
            frame = frame.f_back
        wdbr_thread.stopframe = sys._getframe().f_back
        wdbr_thread.botframe = sys._getframe().f_back
        wdbr_thread.stoplineno = -1
        sys.settrace(wdbr_thread.trace_dispatch)
        return wdbr_thread.trace_dispatch

    threading.settrace(init_new_wdbr)

    # Multiprocess support
    # Monkey patch threading to have callback to kill thread debugger
    old_process_start = multiprocessing.Process.start

    def wdb_process_start(self):
        """Monkey patched start monkey patching run"""
        self.old_run = self.run

        def run(self):
            """Monkey patched run"""
            try:
                self.old_run()
            finally:
                if hasattr(self, '_wdbr'):
                    self._wdbr.die()
        import types
        self.run = types.MethodType(run, self, self.__class__)
        old_process_start(self)
    multiprocessing.Process.start = wdb_process_start

    # Monkey patching fork
    osfork = os.fork

    def tracing_fork():
        pid = osfork()

        if pid == 0:
            wdbr_process = Wdb.make_server()
            sys.settrace(None)

            def trace(frame, event, arg):
                process = multiprocessing.current_process()
                if not hasattr(process, '_wdbr'):
                    process._wdbr = wdbr_process
                wdbr_process.trace_dispatch(frame, event, arg)
                return trace

            frame = sys._getframe()
            while frame:
                frame.f_trace = wdbr_process.trace_dispatch
                wdbr_process.botframe = frame
                frame = frame.f_back
            wdbr_process.stopframe = sys._getframe().f_back
            wdbr_process.stoplineno = -1
            sys.settrace(trace)

        return pid

    if os.fork != tracing_fork:
        os._original_fork = osfork
        os.fork = tracing_fork

    try:
        exec cmd in __main__.__dict__, __main__.__dict__
    except BdbQuit:
        pass
    finally:
        wdbr.quitting = 1
        sys.settrace(None)
        threading.settrace(None)


if __name__ == '__main__':
    main()
