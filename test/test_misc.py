# *-* coding: utf-8 *-*
from .conftest import use


@use('latin-1.py')
def test_latin_1(socket):
    socket.start()
    socket.assert_init()
    socket.send('Continue')
    socket.join()
