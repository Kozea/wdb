# *-* coding: utf-8 *-*
from .conftest import use


@use('latin-1.py')
def test_latin_1(socket):
    socket.start()
    msg = socket.receive()
    assert msg.command == 'Init'
    assert 'cwd' in msg.data
