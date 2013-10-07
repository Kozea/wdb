import wdb


def divide_by_zero(z):
    return z / 0


def with_trace_fun():
    a = 2
    b = 4
    c = a + b
    print(c)
    try:
        d = divide_by_zero(c)
    except ZeroDivisionError:
        d = -1

    print(d)
    print('The end')

wdb.start_trace()
with_trace_fun()
wdb.stop_trace()
