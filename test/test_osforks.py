# *-* coding: utf-8 *-*
from .conftest import use


@use('osfork.py')
def test_with_fork_from_os(socket):
    uuid1 = socket.start()
    uuid2 = socket.start()

    for uuid in (uuid1, uuid2):
        msg = socket.receive(uuid)
        assert msg.command == 'Init'
        assert 'cwd' in msg.data

        msg = socket.receive(uuid)
        assert msg.command == 'Title'
        assert msg.data.title == 'Wdb'
        assert msg.data.subtitle == 'Stepping'

    msg = socket.receive(uuid1)
    assert msg.command == 'Trace'
    current_trace = msg.data.trace[-1]
    if current_trace.code == "print('Children dead')":
        assert current_trace.current is True
        assert 'scripts/osfork.py' in current_trace.file
        assert current_trace.flno == 1
        assert current_trace.function == '<module>'
        assert current_trace.llno == 18
        assert current_trace.lno == 12
        uuid1_fork1 = True
    else:
        assert current_trace.code == "print('Parent dead')"
        assert current_trace.current is True
        assert 'scripts/osfork.py' in current_trace.file
        assert current_trace.flno == 1
        assert current_trace.function == '<module>'
        assert current_trace.llno == 18
        assert current_trace.lno == 16
        uuid1_fork1 = False

    msg = socket.receive(uuid2)
    assert msg.command == 'Trace'
    current_trace = msg.data.trace[-1]
    if uuid1_fork1:
        assert current_trace.code == "print('Parent dead')"
        assert current_trace.current is True
        assert 'scripts/osfork.py' in current_trace.file
        assert current_trace.flno == 1
        assert current_trace.function == '<module>'
        assert current_trace.llno == 18
        assert current_trace.lno == 16
    else:
        assert current_trace.code == "print('Children dead')"
        assert current_trace.current is True
        assert 'scripts/osfork.py' in current_trace.file
        assert current_trace.flno == 1
        assert current_trace.function == '<module>'
        assert current_trace.llno == 18
        assert current_trace.lno == 12

    for uuid in (uuid1, uuid2):
        msg = socket.receive(uuid)
        assert msg.command == 'SelectCheck'
        assert msg.data.frame.function == '<module>'

        msg = socket.receive(uuid)
        assert msg.command == 'Watched'
        assert msg.data == {}

        socket.send('Continue', uuid=uuid)

    socket.join()
