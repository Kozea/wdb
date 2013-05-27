from wdb import trace


def make_error(i):
    try:
        return i / 0
    except ZeroDivisionError:
        return 2

def make_error_in_lib():
    import os.path
    try:
        os.path.join(42, 42)
    except AttributeError:
        return True

with trace():
    a = 2
    b = 4
    c = a + b
    print(c)
    d = make_error(c)
    print(d)

with trace():
    make_error_in_lib()

with trace(full=True):
    make_error_in_lib()


print('The end')
