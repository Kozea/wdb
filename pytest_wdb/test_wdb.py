# -*- coding: utf-8 -*-
from multiprocessing import Process, Lock
from multiprocessing.connection import Listener
import wdb
pytest_plugins = 'pytester',


class FakeWdbServer(Process):
    def __init__(self, stops=False):
        wdb.SOCKET_SERVER = 'localhost'
        wdb.SOCKET_PORT = 18273
        wdb.WDB_NO_BROWSER_AUTO_OPEN = True
        self.stops = stops
        self.lock = Lock()
        super(FakeWdbServer, self).__init__()

    def __enter__(self):
        self.start()
        self.lock.acquire()

    def __exit__(self, *args):
        self.lock.release()
        self.join()
        wdb.Wdb.pop()

    def run(self):
        listener = Listener(('localhost', 18273))
        connection = listener.accept()
        # uuid
        connection.recv_bytes().decode('utf-8')
        # ServerBreaks
        connection.recv_bytes().decode('utf-8')
        # Empty breaks
        connection.send_bytes(b'{}')
        # Continuing
        if self.stops:
            connection.recv_bytes().decode('utf-8')
            connection.send_bytes(b'Continue')

        self.lock.acquire()
        connection.close()
        listener.close()
        self.lock.release()


def test_ok(testdir):
    p = testdir.makepyfile('''
        def test_run():
            print('Test has been run')
    ''')
    with FakeWdbServer():
        result = testdir.runpytest_inprocess('--wdb', p)
    result.stdout.fnmatch_lines([
        'plugins:*wdb*'
    ])
    assert result.ret == 0


def test_ok_run_once(testdir):
    p = testdir.makepyfile('''
        def test_run():
            print('Test has been run')
    ''')

    with FakeWdbServer():
        result = testdir.runpytest_inprocess('--wdb', '-s', p)

    assert len([line for line in result.stdout.lines
                if line == 'test_ok_run_once.py Test has been run']) == 1
    assert result.ret == 0


# Todo implement fake wdb server

def test_fail_run_once(testdir):
    p = testdir.makepyfile('''
        def test_run():
            print('Test has been run')
            assert 0
    ''')
    with FakeWdbServer(stops=True):
        result = testdir.runpytest_inprocess('--wdb', '-s', p)
    assert len([line for line in result.stdout.lines
                if line == 'test_fail_run_once.py Test has been run']) == 1
    assert result.ret == 1


def test_error_run_once(testdir):
    p = testdir.makepyfile('''
        def test_run():
            print('Test has been run')
            1/0
    ''')
    with FakeWdbServer(stops=True):
        result = testdir.runpytest_inprocess('--wdb', '-s', p)
    assert len([line for line in result.stdout.lines
                if line == 'test_error_run_once.py Test has been run']) == 1
    assert result.ret == 1
