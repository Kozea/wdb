from wdb import Wdb
import sys
import multiprocessing
import threading
import os


def main():
    """Inspired by python -m pdb. Debug any python script with wdb"""
    if not sys.argv[1:] or sys.argv[1] in ("--help", "-h"):
        print("usage: wdb.py scriptfile [arg] ...")
        sys.exit(2)

    mainpyfile = sys.argv[1]
    if not os.path.exists(mainpyfile):
        print('Error:', mainpyfile, 'does not exist')
        sys.exit(1)

    del sys.argv[0]
    sys.path[0] = os.path.dirname(mainpyfile)

    # Let's make a server in case of
    wdbr = Wdb.trace()

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

        from wdb._compat import bind
        self.run = bind(self, run)
        old_thread_start(self)
    threading.Thread.start = wdb_thread_start

    def init_new_wdbr(frame, event, args):
        """First settrace call start the debugger for the current thread"""
        import threading
        import sys
        from wdb import Wdb
        thread = threading.currentThread()
        if getattr(thread, 'no_trace', False):
            sys.settrace(None)
            return

        wdbr_thread = Wdb.make_server()
        thread._wdbr = wdbr_thread

        frame = sys._getframe().f_back
        wdbr_thread.stopframe = frame
        wdbr_thread.botframe = frame

        while frame:
            frame.f_trace = wdbr_thread.trace_dispatch
            frame = frame.f_back
        wdbr_thread.stoplineno = -1

        def trace(frame, event, arg):
            rv = wdbr_thread.trace_dispatch(frame, event, arg)
            fn = frame.f_code.co_filename
            if (rv is None and not
                fn == os.path.abspath(fn) and not
                fn.startswith(
                    os.path.dirname(os.path.abspath(sys.argv[0])))):
                return
            return trace

        sys.settrace(trace)
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
        from wdb._compat import bind
        self.run = bind(self, run)
        old_process_start(self)
    multiprocessing.Process.start = wdb_process_start

    # Monkey patching fork
    osfork = os.fork

    def tracing_fork():
        import sys
        import multiprocessing
        from wdb import Wdb
        pid = osfork()

        if pid == 0:
            # Doesn't work with Wdb.trace()...
            sys.settrace(None)
            wdbr_process = Wdb.make_server()

            def trace(frame, event, arg):
                process = multiprocessing.current_process()
                if not hasattr(process, '_wdbr'):
                    process._wdbr = wdbr_process
                rv = wdbr_process.trace_dispatch(frame, event, arg)
                fn = frame.f_code.co_filename
                if (rv is None and
                    fn == os.path.abspath(fn) and not
                    fn.startswith(
                        os.path.dirname(os.path.abspath(sys.argv[0])))):
                    return

                return trace

            frame = sys._getframe().f_back
            wdbr_process.stoplineno = -1
            wdbr_process.stopframe = frame
            while frame:
                frame.f_trace = wdbr_process.trace_dispatch
                wdbr_process.botframe = frame
                frame = frame.f_back
            sys.settrace(trace)

        return pid

    if os.fork != tracing_fork:
        os._original_fork = osfork
        os.fork = tracing_fork

    try:
        Wdb.run_file(mainpyfile)
    finally:
        wdbr.quitting = True
        wdbr.stop_trace(True)


if __name__ == '__main__':
    main()
