# *-* coding: utf-8 *-*
from .conftest import use


@use('trace_in_script.py')
def test_with_trace(socket):
    socket.start()

    msg = socket.receive()
    assert msg.command == 'Init'
    assert 'cwd' in msg.data

    msg = socket.receive()
    assert msg.command == 'Title'
    assert msg.data.title == 'Wdb'
    assert msg.data.subtitle == 'Stepping'

    msg = socket.receive()
    assert msg.command == 'Trace'
    current_trace = msg.data.trace[-1]
    assert current_trace.code == 'a = 2'
    assert current_trace.current is True
    assert 'scripts/trace_in_script.py' in current_trace.file
    assert current_trace.flno == 11
    assert current_trace.function == 'fun2'
    assert current_trace.llno == 15
    assert current_trace.lno == 13

    msg = socket.receive()
    assert msg.command == 'SelectCheck'
    assert msg.data.frame.function == 'fun2'
    file = msg.data.name

    msg = socket.receive()
    assert msg.command == 'Watched'
    assert msg.data == {}

    socket.send('File', file)
    msg = socket.receive()
    assert msg.command == 'Select'
    assert msg.data.name == file
    assert len(msg.data.file) == 261

    socket.send('Continue')

    # Tracing
    msg = None
    while not msg:
        try:
            msg = socket.receive()
        except Exception as e:
            msg = None
            assert type(e) == EOFError

    assert msg.command == 'Title'
    assert msg.data.title == 'Wdb'
    assert msg.data.subtitle == 'Stepping'

    msg = socket.receive()
    assert msg.command == 'Trace'
    current_trace = msg.data.trace[-1]
    assert current_trace.code == "print('The end')"
    assert current_trace.current is True
    assert 'scripts/trace_in_script.py' in current_trace.file
    assert current_trace.flno == 3
    assert current_trace.function == '<module>'
    assert current_trace.llno == 24
    assert current_trace.lno == 24

    msg = socket.receive()
    assert msg.command == 'SelectCheck'
    assert msg.data.frame.function == '<module>'
    file = msg.data.name

    msg = socket.receive()
    assert msg.command == 'Watched'
    assert msg.data == {}

    socket.send('File', file)
    msg = socket.receive()
    assert msg.command == 'Select'
    assert msg.data.name == file
    assert len(msg.data.file) == 261

    socket.send('Continue')
    socket.join()
