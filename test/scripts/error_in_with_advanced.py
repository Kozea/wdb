from wdb import trace


def make_error(i):
    return i / 0


def parent():
    a = 1
    try:
        b = make_error(a)
    except ZeroDivisionError:
        b = 1
    c = 3 * b
    return c


def grandparent():
    a = 2
    b = parent()
    c = a * b
    return c


with trace():
    parent()

with trace(full=True):
    parent()

with trace():
    grandparent()

with trace(full=True):
    grandparent()

print('The end')
