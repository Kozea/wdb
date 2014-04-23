from multiprocessing import Process
from multiprocessing.connection import Listener
from log_colorizer import get_color_logger
from pytest import fixture
from pytest import mark
import pickle
import logging
import signal
import json
import os
import sys


def u(s):
    if sys.version_info[0] == 2:
        return s.decode('utf-8')
    return s


log = get_color_logger('wdb.test')
log.info('Conftest')
log.setLevel(getattr(logging, os.getenv('WDB_TEST_LOG', 'WARNING')))
GLOBALS = globals()
LOCALS = locals()


class Slave(Process):

    def __init__(self, use, host='localhost', port=19999):
        self.argv = None
        self.file = os.path.join(
            os.path.dirname(__file__), 'scripts', use.file)

        if use.with_main:
            self.argv = ['', self.file]
            self.file = os.path.join(
                os.path.dirname(__file__), '..',  'client',
                'wdb', '__main__.py')

        self.host = host
        self.port = port
        super(Slave, self).__init__()

    def run(self):
        import os
        os.environ['WDB_SOCKET_SERVER'] = self.host
        os.environ['WDB_SOCKET_PORT'] = str(self.port)
        os.environ['WDB_NO_BROWSER_AUTO_OPEN'] = 'Yes'
        sys.argv = self.argv

        with open(self.file, 'rb') as file:
            LOCALS['__name__'] = '__main__'
            exec(compile(file.read(), self.file, 'exec'),
                 GLOBALS, LOCALS)


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


class Message(object):
    def __init__(self, message):
        log.info('Received %s' % message)
        pickled = False
        if message.startswith('Server|'):
            message = message.replace('Server|', '')
            pickled = True
        if '|' in message:
            pipe = message.index('|')
            self.command, self.data = message[:pipe], message[pipe + 1:]
            if pickled and self.data:
                self.data = pickle.loads(self.data.encode('utf-8'), protocol=2)
            else:
                self.data = json.loads(self.data, object_hook=AttrDict)
        else:
            self.command, self.data = message, ''


class Socket(object):

    def __init__(self, testfile, host='localhost', port=19999):
        self.slave = Slave(testfile, host, port)
        self.slave.start()
        self.started = False
        self.host = host
        self.port = port
        self.connections = {}
        self.listener = None

    def connection(self, uuid):
        if uuid is None and len(self.connections) == 1:
            return list(self.connections.values())[0]
        else:
            return self.connections[uuid]

    def start(self):
        log.info('Accepting')
        if not self.listener:
            self.listener = Listener((self.host, self.port))
        try:
            connection = self.listener.accept()
        except:
            self.listener.close()
            raise
        self.started = True

        log.info('Connection get')
        uuid = connection.recv_bytes().decode('utf-8')
        self.connections[uuid] = connection
        msg = self.receive(uuid)
        assert msg.command == 'ServerBreaks'
        self.send('[]', uuid=uuid)
        self.send('Start', uuid=uuid)
        return uuid

    def assert_init(self):
        assert self.receive().command == 'Init'
        assert self.receive().command == 'Title'
        assert self.receive().command == 'Trace'
        assert self.receive().command == 'SelectCheck'
        echo_watched = self.receive().command
        if echo_watched == 'Echo':
            echo_watched = self.receive().command
        assert echo_watched == 'Watched'

    def assert_position(self, title=None, subtitle=None, file=None,
                        code=None, function=None, line=None,
                        breaks=None):
        titlemsg = self.receive()
        assert titlemsg.command == 'Title'
        if title is not None:
            assert titlemsg.data.title == title
        if subtitle is not None:
            assert titlemsg.data.subtitle == subtitle
        tracemsg = self.receive()

        assert tracemsg.command == 'Trace'
        last = tracemsg.data.trace[-1]
        if file is not None:
            assert last.file == file
        if code is not None:
            assert last.code == code
        if function is not None:
            assert last.function == function
        if line is not None:
            assert last.lno == line

        selectmsg = self.receive()
        assert selectmsg.command == 'SelectCheck'

        assert self.receive().command == 'Watched'

    def receive(self, uuid=None):
        return Message(self.connection(uuid).recv_bytes().decode('utf-8'))

    def send(self, command, data=None, uuid=None):
        message = '%s|%s' % (command, data) if data else command
        log.info('Sending %s' % message)
        self.connection(uuid).send_bytes(message.encode('utf-8'))

    def join(self):
        self.slave.join()

    def close(self, failed=False):
        slave_was_alive = False
        if self.slave.is_alive():
            self.slave.terminate()
            slave_was_alive = True

        if self.started:
            for connection in self.connections.values():
                connection.close()
            self.listener.close()

        if slave_was_alive and not failed:
            raise Exception('Tests must join the subprocess')


class use(object):
    def __init__(self, file, with_main=False):
        self.file = file
        self.with_main = with_main

    def __call__(self, fun):
        fun._wdb_use = self
        return fun


def timeout_handler(signum, frame):
    raise Exception('Timeout')

signal.signal(signal.SIGALRM, timeout_handler)


@fixture(scope="function")
def socket(request):
    log.info('Fixture')
    socket = Socket(request.function._wdb_use,
                    port=sys.hexversion % 60000 + 1024)

    # If it takes more than 5 seconds, it must be an error
    if not os.getenv('NO_WDB_TIMEOUT'):
        signal.alarm(5)

    def end_socket():
        failed = False
        if hasattr(request.node, 'rep_call'):
            failed = request.node.rep_call.failed
        socket.close(failed)
        signal.alarm(0)

    request.addfinalizer(end_socket)
    return socket


@mark.tryfirst
def pytest_runtest_makereport(item, call, __multicall__):
    """Give test status information to finalizer"""
    rep = __multicall__.execute()
    setattr(item, "rep_" + rep.when, rep)
    return rep
