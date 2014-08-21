from .conftest import use


@use('ok_script.py', with_main=True)
def test_main_on_running_script(socket):
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
    assert current_trace.code == 'a = 3'
    assert current_trace.current is True
    assert 'scripts/ok_script.py' in current_trace.file
    assert current_trace.flno == 1
    assert current_trace.function == '<module>'
    assert current_trace.llno == 4
    assert current_trace.lno == 1

    msg = socket.receive()
    assert msg.command == 'SelectCheck'
    assert msg.data.frame.function == '<module>'

    msg = socket.receive()
    assert msg.command == 'Watched'
    assert msg.data == {}

    socket.send('Next')
    socket.assert_position(code='b = 5')
    socket.send('Next')
    socket.assert_position(code='c = a + b')
    socket.send('Continue')
    socket.join()


@use('404.py', with_main=True)
def test_main_on_unexisting_script(socket):
    # If it doesn't timeout this is good
    socket.join()
