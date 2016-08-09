# *-* coding: utf-8 *-*
from .conftest import use


@use('movement.py')
def test_next(socket):
    socket.start()
    socket.assert_init()

    def next(code):
        socket.send('Next')
        socket.assert_position(code=code)

    next('l.append(3)')
    next('l += [8, 12]')
    next('l = modify_list(l)')
    for i in range(3):
        next('for i, e in enumerate(l[:]):')
        next('if i > 2:')
        next('l[i] = e * i')

    next('for i, e in enumerate(l[:]):')
    next('if i > 2:')
    next('l[i] = i')

    next('for i, e in enumerate(l[:]):')
    next('print(l, sum(l))')

    socket.send('Continue')
    socket.join()


@use('movement.py')
def test_until(socket):
    socket.start()
    socket.assert_init()

    def until(code):
        socket.send('Until')
        socket.assert_position(code=code)

    until('l.append(3)')
    until('l += [8, 12]')
    until('l = modify_list(l)')
    until('for i, e in enumerate(l[:]):')
    until('if i > 2:')
    until('l[i] = e * i')
    until('print(l, sum(l))')

    socket.send('Continue')
    socket.join()


@use('movement.py')
def test_step(socket):
    socket.start()
    socket.assert_init()

    def step(code, **kwargs):
        socket.send('Step')
        socket.assert_position(code=code, **kwargs)

    step('l.append(3)')
    step('l += [8, 12]')
    step('l = modify_list(l)')
    step('def modify_list(ll):', call="modify_list(ll=[\n  <a href=")
    step('ll[1] = 7')
    step('ll.insert(0, 3)')
    step('return ll')
    step('return ll', return_="[\n  <a href=")

    for i in range(3):
        step('for i, e in enumerate(l[:]):')
        step('if i > 2:')
        step('l[i] = e * i')

    step('for i, e in enumerate(l[:]):')
    step('if i > 2:')
    step('l[i] = i')

    step('for i, e in enumerate(l[:]):')
    step('print(l, sum(l))')

    socket.send('Continue')
    socket.join()


@use('movement.py')
def test_return(socket):
    socket.start()
    socket.assert_init()

    def ret(code, **kwargs):
        socket.send('Return')
        socket.assert_position(code=code, **kwargs)

    def step(code, **kwargs):
        socket.send('Step')
        socket.assert_position(code=code, **kwargs)

    step('l.append(3)')
    step('l += [8, 12]')
    step('l = modify_list(l)')
    step('def modify_list(ll):', call="modify_list(ll=[\n  <a href=")
    step('ll[1] = 7')
    ret('return ll', return_="[\n  <a href=")

    for i in range(3):
        step('for i, e in enumerate(l[:]):')
        step('if i > 2:')
        step('l[i] = e * i')

    step('for i, e in enumerate(l[:]):')
    step('if i > 2:')
    step('l[i] = i')

    step('for i, e in enumerate(l[:]):')
    step('print(l, sum(l))')

    socket.send('Continue')
    socket.join()
