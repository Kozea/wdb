import wdb


def divide_by_zero(z):
    return z / 0


def with_trace_fun():
    a = 2
    b = 4
    c = a + b
    print(c)
    d = divide_by_zero(c)
    print(d)
    print('The end')

wdb.start_trace()
try:
    with_trace_fun()
finally:
    wdb.stop_trace()
