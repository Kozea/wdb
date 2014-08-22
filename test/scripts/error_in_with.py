from wdb import trace


def make_error(i):
    try:
        return i / 0
    except ZeroDivisionError:
        return 2

with trace():
    a = 2
    b = 4
    c = a + b
    print(c)
    d = make_error(c)
    print(d)

with trace(full=True):
    a = 2
    b = 4
    c = a + b
    print(c)
    d = make_error(c)
    print(d + a)


print('The end')
