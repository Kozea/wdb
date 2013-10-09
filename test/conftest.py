from multiprocessing import Process
from multiprocessing.connection import Listener
from log_colorizer import get_color_logger
from pytest import fixture
from logging import getLevelName
import signal
import json
import os
import sys


log = get_color_logger('wdb.test')
log.info('Conftest')
log.setLevel(getLevelName(os.getenv('WDB_TEST_LOG', 'WARNING')))
GLOBALS = globals()
LOCALS = locals()


class Slave(Process):

    def __init__(self, file, host='localhost', port=19999):
        self.file = os.path.join(
            os.path.dirname(__file__), 'scripts', file)
        self.host = host
        self.port = port
        super(Slave, self).__init__()

    def run(self):
        import os
        os.environ['WDB_SOCKET_SERVER'] = self.host
        os.environ['WDB_SOCKET_PORT'] = str(self.port)
        os.environ['WDB_NO_BROWSER_AUTO_OPEN'] = 'Yes'

        with open(self.file, 'rb') as file:
            exec(compile(file.read(), self.file, 'exec'),
                 GLOBALS, LOCALS)


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


class Message(object):
    def __init__(self, message):
        log.info('Received %s' % message)
        if '|' in message:
            pipe = message.index('|')
            self.command, self.data = message[:pipe], message[pipe + 1:]
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
        self.send('Start', uuid=uuid)
        return uuid

    def init(self):
        self.start()
        assert self.receive().command == 'Init'
        assert self.receive().command == 'Title'
        assert self.receive().command == 'Trace'
        assert self.receive().command == 'SelectCheck'
        assert self.receive().command == 'Echo'
        echo_watched = self.receive().command
        if echo_watched == 'Echo':
            echo_watched = self.receive().command
        assert echo_watched == 'Watched'

    def receive(self, uuid=None):
        return Message(self.connection(uuid).recv_bytes().decode('utf-8'))

    def send(self, command, data=None, uuid=None):
        message = '%s|%s' % (command, data) if data else command
        log.info('Sending %s' % message)
        self.connection(uuid).send_bytes(message.encode('utf-8'))

    def close(self):
        self.slave.terminate()
        if self.started:
            for connection in self.connections.values():
                connection.close()
            self.listener.close()


class use(object):
    def __init__(self, file):
        self.file = file

    def __call__(self, fun):
        fun._wdb_file = self.file
        return fun


def timeout_handler(signum, frame):
    raise Exception('Timeout')

signal.signal(signal.SIGALRM, timeout_handler)


@fixture(scope="function")
def socket(request):
    log.info('Fixture')
    socket = Socket(request.function._wdb_file,
                    port=sys.hexversion % 60000 + 1024)

    # If it takes more than 5 seconds, it must be an error
    signal.alarm(5)

    def end_socket():
        signal.alarm(0)
        socket.close()

    request.addfinalizer(end_socket)
    return socket
