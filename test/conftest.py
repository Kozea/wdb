from multiprocessing import Process
from multiprocessing.connection import Listener
from log_colorizer import get_color_logger
from pytest import fixture
import logging
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

    def run(self, *args):
        import os
        os.environ['WDB_SOCKET_SERVER'] = self.host
        os.environ['WDB_SOCKET_PORT'] = str(self.port)
        os.environ['WDB_NO_BROWSER_AUTO_OPEN'] = 'Yes'

        with open(self.file) as file:
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

    def __init__(self, host='localhost', port=19999):
        log.info('Opening socket')
        self.listener = Listener((host, port))
        log.info('Accepting')
        self.connection = self.listener.accept()
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
        self.connection.close()
        self.listener.close()


@fixture(scope="function")
def socket(request):
    log.info('Fixture')
    slave = Slave('error_in_script.py')
    slave.start()
    socket = Socket()

    def end_socket():
        socket.close()
        slave.terminate()

    request.addfinalizer(end_socket)
    return socket
