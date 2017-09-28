# *-* coding: utf-8 *-*
from .conftest import use


@use('objects.py')
def test_repr(socket):
    socket.start()

    def step(code, **kwargs):
        socket.send('Step')
        socket.assert_position(code=code, **kwargs)

    def next(code, **kwargs):
        socket.send('Next')
        socket.assert_position(code=code, **kwargs)

    msg = socket.receive()
    assert msg.command == 'Init'
    assert 'cwd' in msg.data

    msg = socket.receive()
    assert msg.command == 'Title'
    assert msg.data.title == 'Wdb'
    assert msg.data.subtitle == 'Stepping'

    msg = socket.receive()
    assert msg.command == 'Trace'

    msg = socket.receive()
    assert msg.command == 'SelectCheck'
    file = msg.data.name

    msg = socket.receive()
    assert msg.command == 'Watched'
    assert msg.data == {}

    socket.send('File', file)
    msg = socket.receive()
    assert msg.command == 'Select'
    assert msg.data.name == file

    def link(var):
        return '<a href="%d" class="inspect">%r</a>' % (id(var), var)

    step('def create_a(n):', call='create_a(n=%s)' % link(5))
    next('a = A(n)')
    next('return a')
    next('return a', return_='&lt;A object with n=5&gt;')
    next('b = create_a(2)')
    next('a, b, c = combine(a, b)')
    step('def combine(a, b):', call='&lt;A object with n=5&gt;')

    next('return [a, b, A(a.n + b.n)]')
    next('return [a, b, A(a.n + b.n)]', return_='&lt;A object with n=7&gt;')
    next('display(a, b, wdb, c=c, cls=A, obj=object)')
    step(
        'def display(a, b=None, *c, **d):', call=' class="inspect">&lt;class '
    )
    next('print(locals())')
    next('print(locals())', return_='None')

    socket.send('Continue')
    socket.join()
