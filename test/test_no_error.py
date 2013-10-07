# *-* coding: utf-8 *-*
from .conftest import use


@use('error_ignored_in_script.py')
def test_with_error_ignored(socket):
    socket.slave.join()


@use('error_not_ignored_in_script.py')
def test_with_error_not_ignored_because_of_full(socket):
    socket.start()
    msg = socket.receive()
    assert msg.command == 'Init'
    assert 'cwd' in msg.data
