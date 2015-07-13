

def fun1(a):
    b = 4
    c = a + b
    for i in range(10):
        c += b
    return c + 1


def fun2(l):
    import wdb
    wdb.set_trace()
    a = 2
    e = fun1(a)
    return e


def main():
    fun2(0)


main()
import wdb
wdb.set_trace()
print('The end')
