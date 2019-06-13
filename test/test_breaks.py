# *-* coding: utf-8 *-*
from .conftest import use
import json
import os


def make_break(
    fn='movement.py', lno=None, cond=None, fun=None, temporary=False
):
    return json.dumps(
        {
            'fn': os.path.join(os.path.dirname(__file__), 'scripts', fn),
            'lno': lno,
            'cond': cond,
            'fun': fun,
            'temporary': temporary,
        }
    )


@use('movement.py')
def test_simple_break(socket):
    socket.start()
    socket.assert_init()
    socket.send('Break', make_break('movement.py', 7))
    msg = socket.receive()
    assert msg.command == 'BreakSet'
    socket.send('Next')
    socket.assert_position(line=12, breaks=[7])
    socket.send('Continue')
    socket.assert_position(line=7)
    socket.send('Next')
    socket.assert_position(line=8)

    socket.send('Continue')
    socket.join()


@use('movement.py')
def test_function_break(socket):
    socket.start()
    socket.assert_init()

    socket.send('Break', make_break(fun='modify_list'))
    msg = socket.receive()
    assert msg.command == 'BreakSet'
    socket.send('Next')
    socket.assert_position(line=12)
    socket.send('Continue')
    socket.assert_position(line=6)
    socket.send('Next')
    socket.assert_position(line=7)
    socket.send('Next')
    socket.assert_position(line=8)
    socket.send('Unbreak', make_break(fun='modify_list'))
    msg = socket.receive()
    assert msg.command == 'BreakUnset'

    socket.send('Continue')
    socket.join()


@use('movement.py')
def test_conditional_break(socket):
    socket.start()
    socket.assert_init()

    socket.send('Break', make_break(cond='sum(l) > 28'))
    msg = socket.receive()
    assert msg.command == 'BreakSet'
    socket.send('Next')
    socket.assert_position(line=12)
    socket.send('Continue')

    socket.assert_position(line=16)
    socket.send('Unbreak', make_break(cond='sum(l) > 28'))
    msg = socket.receive()
    assert msg.command == 'BreakUnset'

    socket.send('Continue')
    socket.join()
