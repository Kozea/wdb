# *-* coding: utf-8 *-*
from .utils import division_by_zero_message


def test_init(socket):
    msg = socket.receive()
    assert msg.command == 'Init'
    assert 'cwd' in msg.data

    msg = socket.receive()
    assert msg.command == 'Title'
    assert msg.data.title == 'ZeroDivisionError'
    assert msg.data.subtitle == division_by_zero_message

    msg = socket.receive()
    assert msg.command == 'Trace'
    current_trace = msg.data.trace[-1]
    assert current_trace.code == 'return z / 0'
    assert current_trace.current is False
    assert 'scripts/error_in_script.py' in current_trace.file
    assert current_trace.flno == 4
    assert current_trace.function == 'divide_by_zero'
    assert current_trace.llno == 5
    assert current_trace.lno == 5

    msg = socket.receive()
    assert msg.command == 'SelectCheck'
    assert msg.data.breaks == []
    assert msg.data.frame.function == 'divide_by_zero'
    file = msg.data.name

    msg = socket.receive()
    assert msg.command == 'Echo'
    assert msg.data['for'] == '__exception__'
    assert msg.data.val == ("ZeroDivisionError: %s" %
                            division_by_zero_message)

    msg = socket.receive()
    assert msg.command == 'Watched'
    assert msg.data == {}

    socket.send('File', file)
    msg = socket.receive()
    assert msg.command == 'Select'
    assert msg.data.name == file
    assert len(msg.data.file) == 259

    socket.send('Continue')
    try:
        msg = socket.receive()
    except Exception as e:
        assert type(e) == EOFError
