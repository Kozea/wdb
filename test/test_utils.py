# *-* coding: utf-8 *-*
import sys


def test_args():
    from wdb.utils import get_args

    def f(i, j):
        assert get_args(sys._getframe()) == 'i=%r, j=%r' % (i, j)
    f(10, 'a')
    f(None, 2 + 7j)


def test_empty():
    from wdb.utils import get_args

    def f():
        assert get_args(sys._getframe()) == ''
    f()


def test_arg_with_default():
    from wdb.utils import get_args

    def f(x, y=12, z=2193):
        assert get_args(sys._getframe()) == 'x=%r, y=%r, z=%r' % (x, y, z)
    f(5)
    f('a')
    f('a', 5, 19)
    f('a', z=19)


def test_varargs():
    from wdb.utils import get_args

    def f(x, *args):
        assert get_args(sys._getframe()) == 'x=%r, *args=%r' % (x, args)
    f(2, 3, 5, 'a')
    f(2, *[[1, 2], 3])
    f(2)


def test_varargs_only():
    from wdb.utils import get_args

    def f(*a):
        assert get_args(sys._getframe()) == '*a=%r' % (a,)
    f(5, 2)
    f(10)
    f()


def test_kwargs():
    from wdb.utils import get_args

    def f(x, **kwargs):
        assert get_args(sys._getframe()) == 'x=%r, **kwargs=%r' % (x, kwargs)

    f(5)
    f(9, i=4, j=53)
    f(1, i=4, **{'d': 5, 'c': 'c'})


def test_kwargs_only():
    from wdb.utils import get_args

    def f(**kw):
        assert get_args(sys._getframe()) == '**kw=%r' % kw

    f()
    f(a='i', b=5)
    f(d={'i': 3})
    f(**{'d': 5, 'c': 'c'})


def test_method():
    from wdb.utils import get_args

    class cls(object):
        def f(self, a, b=2, *args, **kwargs):
            assert get_args(sys._getframe()) == (
                'self=%r, a=%r, b=%r, *args=%r, **kwargs=%r' % (
                    (self, a, b, args, kwargs)))

    obj = cls()
    obj.f(8, 'p', 8, z=2, o=9)
    obj.f(None)
