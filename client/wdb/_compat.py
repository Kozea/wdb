import codecs
import re
import sys

python_version = sys.version_info[0]

try:
    from json import loads, dumps, JSONEncoder
except ImportError:
    from simplejson import loads, dumps, JSONEncoder

try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote

try:
    from html import escape
except ImportError:
    from cgi import escape

try:
    from socketserver import TCPServer
except ImportError:
    from SocketServer import TCPServer

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

if python_version == 2:
    from StringIO import StringIO
else:
    from io import StringIO

if python_version == 2:

    def execute(cmd, globals_, locals_):
        exec('exec cmd in globals_, locals_')


else:

    def execute(cmd, globals_, locals_):
        exec(cmd, globals_, locals_)


_cookie_search = re.compile(r"coding[:=]\s*([-\w.]+)").search


def _detect_encoding(filename):
    import linecache

    lines = linecache.getlines(filename)
    return _detect_lines_encoding(lines)


def _detect_lines_encoding(lines):
    if not lines or lines[0].startswith(u("\xef\xbb\xbf")):
        return "utf-8"
    magic = _cookie_search("".join(lines[:2]))
    if magic is None:
        return 'utf-8'
    encoding = magic.group(1)
    try:
        codecs.lookup(encoding)
    except LookupError:
        return 'utf-8'
    return encoding


if python_version == 2:
    basestr = basestring

    def to_unicode(string):
        return string.decode('utf-8')

    def to_unicode_string(string, filename):
        if isinstance(string, unicode):
            return string

        encoding = _detect_encoding(filename)
        if encoding != 'utf-8' and string:
            return string.decode(encoding).encode('utf-8')
        else:
            return string

    def to_bytes(string):
        return string

    def from_bytes(bytes_):
        return bytes_

    def force_bytes(bytes_):
        if isinstance(bytes_, unicode):
            return bytes_.encode('utf-8')
        return bytes_


else:
    basestr = (str, bytes)

    def to_unicode(string):
        return string

    def to_unicode_string(string, filename):
        return string

    def to_bytes(string):
        return string.encode('utf-8')

    def from_bytes(bytes_):
        return bytes_.decode('utf-8')

    def force_bytes(bytes_):
        if isinstance(bytes_, str):
            return bytes_.encode('utf-8')
        return bytes_


def is_str(string):
    return isinstance(string, basestr)


def u(s):
    if python_version == 2:
        return s.decode('utf-8')
    return s


if python_version == 2:
    import struct
    import socket
    import errno
    import time
    import select

    has_winapi = False
    try:
        import _winapi

        has_winapi = True
    except ImportError:
        pass

    if sys.platform == 'win32' and has_winapi:
        from _winapi import WAIT_OBJECT_0, WAIT_TIMEOUT, INFINITE

        try:
            from _winapi import WAIT_ABANDONED_0
        except ImportError:
            WAIT_ABANDONED_0 = 128

        def _exhaustive_wait(handles, timeout):
            # Return ALL handles which are currently signalled.  (Only
            # returning the first signalled might create starvation issues.)
            L = list(handles)
            ready = []
            while L:
                res = _winapi.WaitForMultipleObjects(L, False, timeout)
                if res == WAIT_TIMEOUT:
                    break
                elif WAIT_OBJECT_0 <= res < WAIT_OBJECT_0 + len(L):
                    res -= WAIT_OBJECT_0
                elif WAIT_ABANDONED_0 <= res < WAIT_ABANDONED_0 + len(L):
                    res -= WAIT_ABANDONED_0
                else:
                    raise RuntimeError('Should not get here')
                ready.append(L[res])
                L = L[res + 1 :]
                timeout = 0
            return ready

        _ready_errors = set(
            (_winapi.ERROR_BROKEN_PIPE, _winapi.ERROR_NETNAME_DELETED)
        )

        def wait(object_list, timeout=None):
            '''
            Wait till an object in object_list is ready/readable.
            Returns list of those objects in object_list which are
            ready/readable.
            '''
            if timeout is None:
                timeout = INFINITE
            elif timeout < 0:
                timeout = 0
            else:
                timeout = int(timeout * 1000 + 0.5)

            object_list = list(object_list)
            waithandle_to_obj = {}
            ov_list = []
            ready_objects = set()
            ready_handles = set()

            try:
                for o in object_list:
                    try:
                        fileno = getattr(o, 'fileno')
                    except AttributeError:
                        waithandle_to_obj[o.__index__()] = o
                    else:
                        # start an overlapped read of length zero
                        try:
                            ov, err = _winapi.ReadFile(fileno(), 0, True)
                        except OSError as e:
                            err = e.winerror
                            if err not in _ready_errors:
                                raise
                        if err == _winapi.ERROR_IO_PENDING:
                            ov_list.append(ov)
                            waithandle_to_obj[ov.event] = o
                        else:
                            # If o.fileno() is an overlapped pipe handle and
                            # err == 0 then there is a zero length message
                            # in the pipe, but it HAS NOT been consumed.
                            ready_objects.add(o)
                            timeout = 0

                ready_handles = _exhaustive_wait(
                    waithandle_to_obj.keys(), timeout
                )
            finally:
                # request that overlapped reads stop
                for ov in ov_list:
                    ov.cancel()

                # wait for all overlapped reads to stop
                for ov in ov_list:
                    try:
                        _, err = ov.GetOverlappedResult(True)
                    except OSError as e:
                        err = e.winerror
                        if err not in _ready_errors:
                            raise
                    if err != _winapi.ERROR_OPERATION_ABORTED:
                        o = waithandle_to_obj[ov.event]
                        ready_objects.add(o)
                        if err == 0:
                            # If o.fileno() is an overlapped pipe handle then
                            # a zero length message HAS been consumed.
                            if hasattr(o, '_got_empty_message'):
                                o._got_empty_message = True

            ready_objects.update(waithandle_to_obj[h] for h in ready_handles)
            return [p for p in object_list if p in ready_objects]

    else:
        if hasattr(select, 'poll'):

            def _poll(fds, timeout):
                if timeout is not None:
                    timeout = int(timeout * 1000)  # timeout is in milliseconds
                fd_map = {}
                pollster = select.poll()
                for fd in fds:
                    pollster.register(fd, select.POLLIN)
                    if hasattr(fd, 'fileno'):
                        fd_map[fd.fileno()] = fd
                    else:
                        fd_map[fd] = fd
                ls = []
                for fd, event in pollster.poll(timeout):
                    if event & select.POLLNVAL:
                        raise ValueError('invalid file descriptor %i' % fd)
                    ls.append(fd_map[fd])
                return ls

        else:

            def _poll(fds, timeout):
                return select.select(fds, [], [], timeout)[0]

        def wait(object_list, timeout=None):
            '''
            Wait till an object in object_list is ready/readable.
            Returns list of those objects in object_list which are
             ready/readable.
            '''
            if timeout is not None:
                if timeout <= 0:
                    return _poll(object_list, 0)
                else:
                    deadline = time.time() + timeout
            while True:
                try:
                    return _poll(object_list, timeout)
                except OSError as e:
                    if e.errno != errno.EINTR:
                        raise
                if timeout is not None:
                    timeout = deadline - time.time()

    class Socket(object):
        """A Socket compatible with multiprocessing.connection.Client, that
        uses socket objects."""

        # https://github.com/akheron/cpython/blob/3.3/Lib/multiprocessing/connection.py#L349
        def __init__(self, address):
            self._handle = socket.socket()
            self._handle.connect(address)
            self._handle.setblocking(1)

        def send_bytes(self, buf):
            self._check_closed()
            n = len(buf)
            # For wire compatibility with 3.2 and lower
            header = struct.pack("!i", n)
            if n > 16384:
                # The payload is large so Nagle's algorithm won't be triggered
                # and we'd better avoid the cost of concatenation.
                chunks = [header, buf]
            elif n > 0:
                # Issue #20540: concatenate before sending, to avoid delays
                # dueto Nagle's algorithm on a TCP socket.
                chunks = [header + buf]
            else:
                # This code path is necessary to avoid "broken pipe" errors
                # when sending a 0-length buffer if the other end closed the
                # pipe.
                chunks = [header]
            for chunk in chunks:
                self._handle.sendall(chunk)

        def _safe_recv(self, *args, **kwargs):
            while True:
                try:
                    return self._handle.recv(*args, **kwargs)
                except socket.error as e:
                    # Interrupted system call
                    if e.errno != errno.EINTR:
                        raise

        def recv_bytes(self):
            self._check_closed()
            size, = struct.unpack("!i", self._safe_recv(4))
            return self._safe_recv(size)

        def _check_closed(self):
            if self._handle is None:
                raise IOError("handle is closed")

        def close(self):
            self._check_closed()
            self._handle.close()
            self._handle = None

        def poll(self, timeout=0.0):
            """Whether there is any input available to be read"""
            self._check_closed()
            return self._poll(timeout)

        def _poll(self, timeout):
            r = wait([self._handle], timeout)
            return bool(r)


else:
    from multiprocessing.connection import Client as Socket

try:
    from importlib.util import find_spec
    from importlib import import_module

    def existing_module(module):
        return bool(find_spec(module))


except ImportError:
    import imp

    def existing_module(module):
        try:
            imp.find_module(module)
            return True
        except ImportError:
            return False

    def import_module(module):
        __import__(module)
        if module not in sys.modules:
            raise ImportError(module)
        return sys.modules[module]


# Not really compat but convenient
try:
    from log_colorizer import get_color_logger
except ImportError:
    import logging

    logger = logging.getLogger
else:
    logger = get_color_logger
