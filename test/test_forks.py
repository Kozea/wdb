# *-* coding: utf-8 *-*
from .conftest import use


@use('forks.py')
def test_with_forks(socket):
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
    if current_trace.code == "print('Process 1 end')":
        assert current_trace.current is True
        assert 'scripts/forks.py' in current_trace.file
        assert current_trace.flno == 6
        assert current_trace.function == 'run'
        assert current_trace.llno == 9
        assert current_trace.lno == 9
        uuid1_fork1 = True
    else:
        assert current_trace.code == "print('Process 2 end')"
        assert current_trace.current is True
        assert 'scripts/forks.py' in current_trace.file
        assert current_trace.flno == 13
        assert current_trace.function == 'run'
        assert current_trace.llno == 16
        assert current_trace.lno == 16
        uuid1_fork1 = False

    msg = socket.receive(uuid2)
    assert msg.command == 'Trace'
    current_trace = msg.data.trace[-1]
    if uuid1_fork1:
        assert current_trace.code == "print('Process 2 end')"
        assert current_trace.current is True
        assert 'scripts/forks.py' in current_trace.file
        assert current_trace.flno == 13
        assert current_trace.function == 'run'
        assert current_trace.llno == 16
        assert current_trace.lno == 16
    else:
        assert current_trace.code == "print('Process 1 end')"
        assert current_trace.current is True
        assert 'scripts/forks.py' in current_trace.file
        assert current_trace.flno == 6
        assert current_trace.function == 'run'
        assert current_trace.llno == 9
        assert current_trace.lno == 9

    for uuid in (uuid1, uuid2):
        msg = socket.receive(uuid)
        assert msg.command == 'SelectCheck'
        assert msg.data.frame.function == 'run'

        msg = socket.receive(uuid)
        assert msg.command == 'Watched'
        assert msg.data == {}

        socket.send('Continue', uuid=uuid)

    last_uuid = socket.start()
    msg = socket.receive(last_uuid)
    assert msg.command == 'Init'
    assert 'cwd' in msg.data

    msg = socket.receive(last_uuid)
    assert msg.command == 'Title'
    assert msg.data.title == 'Wdb'
    assert msg.data.subtitle == 'Stepping'

    msg = socket.receive(last_uuid)
    assert msg.command == 'Trace'
    current_trace = msg.data.trace[-1]
    assert current_trace.code == "print('The End')"
    assert current_trace.current is True
    assert 'scripts/forks.py' in current_trace.file
    assert current_trace.flno == 1
    assert current_trace.function == '<module>'
    assert current_trace.llno == 30
    assert current_trace.lno == 30

    socket.send('Continue', uuid=last_uuid)
    socket.join()
