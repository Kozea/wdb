from multiprocessing import Process
from multiprocessing.connection import Listener
from log_colorizer import get_color_logger
from pytest import fixture
import signal
import json
import os


log = get_color_logger('wdb.test')
log.info('Conftest')
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

    def __init__(self, slave, host='localhost', port=19999):
        self.slave = slave
        self.slave.start()
        self.started = False
        self.host = host
        self.port = port

    def start(self):
        log.info('Opening socket')
        self.listener = Listener((self.host, self.port))
        log.info('Accepting')
        try:
            self.connection = self.listener.accept()
        except:
            self.listener.close()
            raise
        self.started = True
        log.info('Connection get')
        # uuid is a particular case
        self.uuid = self.receive().command
        self.send('Start')

    def receive(self):
        return Message(self.connection.recv_bytes().decode('utf-8'))

    def send(self, command, data=None):
        message = '%s|%s' % (command, data) if data else command
        log.info('Sending %s' % message)
        self.connection.send_bytes(message.encode('utf-8'))

    def close(self):
        self.slave.terminate()
        if self.started:
            self.connection.close()
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
    socket = Socket(Slave(request.function._wdb_file))

    # If it takes more than 5 seconds, it must be an error
    signal.alarm(5)

    def end_socket():
        signal.alarm(0)
        socket.close()

    request.addfinalizer(end_socket)
    return socket
