# *-* coding: utf-8 *-*
import sys

from wdb._compat import OrderedDict


def test_args():
    from wdb.utils import get_args

    def f(i, j):
        assert get_args(sys._getframe()) == OrderedDict((('i', i), ('j', j)))

    f(10, 'a')
    f(None, 2 + 7j)


def test_empty():
    from wdb.utils import get_args

    def f():
        assert get_args(sys._getframe()) == OrderedDict()

    f()


def test_arg_with_default():
    from wdb.utils import get_args

    def f(x, y=12, z=2193):
        assert get_args(sys._getframe()) == OrderedDict(
            (('x', x), ('y', y), ('z', z))
        )

    f(5)
    f('a')
    f('a', 5, 19)
    f('a', z=19)


def test_varargs():
    from wdb.utils import get_args

    def f(x, *args):
        assert get_args(sys._getframe()) == OrderedDict(
            (('x', x), ('*args', args))
        )

    f(2, 3, 5, 'a')
    f(2, *[[1, 2], 3])
    f(2)


def test_varargs_only():
    from wdb.utils import get_args

    def f(*a):
        assert get_args(sys._getframe()) == OrderedDict((('*a', a),))

    f(5, 2)
    f(10)
    f()


def test_kwargs():
    from wdb.utils import get_args

    def f(x, **kwargs):
        assert get_args(sys._getframe()) == OrderedDict(
            (('x', x), ('**kwargs', kwargs))
        )

    f(5)
    f(9, i=4, j=53)
    f(1, i=4, **{'d': 5, 'c': 'c'})


def test_kwargs_only():
    from wdb.utils import get_args

    def f(**kw):
        assert get_args(sys._getframe()) == OrderedDict((('**kw', kw),))

    f()
    f(a='i', b=5)
    f(d={'i': 3})
    f(**{'d': 5, 'c': 'c'})


def test_method():
    from wdb.utils import get_args

    class cls(object):
        def f(self, a, b=2, *args, **kwargs):
            assert get_args(sys._getframe()) == OrderedDict(
                (
                    ('self', self),
                    ('a', a),
                    ('b', b),
                    ('*args', args),
                    ('**kwargs', kwargs),
                )
            )

    obj = cls()
    obj.f(8, 'p', 10, z=2, o=9)
    obj.f(None)


if sys.version_info[0] >= 3:
    # ...
    exec(
        '''
def test_method_reverse():
    from wdb.utils import get_args

    class cls(object):
        def f(self, a, *args, b=2, **kwargs):
            assert get_args(sys._getframe()) == OrderedDict((
                ('self', self),
                ('a', a),
                ('*args', args),
                ('b', b),
                ('**kwargs', kwargs)
            ))

    obj = cls()
    obj.f(8, 'p', 10, z=2, o=9)
    obj.f(8, 10, z=2, o=9, b='p')
    obj.f(None)


def test_complicated():
    from wdb.utils import get_args

    def f(a, b, c, d=5, e=12, *args, h=1, i=8, j=None, **kwargs):
        assert get_args(sys._getframe()) == OrderedDict((
            ('a', a),
            ('b', b),
            ('c', c),
            ('d', d),
            ('e', e),
            ('*args', args),
            ('h', h),
            ('i', i),
            ('j', j),
            ('**kwargs', kwargs)
        ))

    def g(a, b, c, *args, h=1, i=8, j=None, **kwargs):
        assert get_args(sys._getframe()) == OrderedDict((
            ('a', a),
            ('b', b),
            ('c', c),
            ('*args', args),
            ('h', h),
            ('i', i),
            ('j', j),
            ('**kwargs', kwargs)
        ))

    def h(a, b, c, h=1, i=8, j=None, **kwargs):
        assert get_args(sys._getframe()) == OrderedDict((
            ('a', a),
            ('b', b),
            ('c', c),
            ('h', h),
            ('i', i),
            ('j', j),
            ('**kwargs', kwargs)
        ))

    def i(a, b, c, *args, h=1, i=8, j=None):
        assert get_args(sys._getframe()) == OrderedDict((
            ('a', a),
            ('b', b),
            ('c', c),
            ('*args', args),
            ('h', h),
            ('i', i),
            ('j', j),
        ))

    def j(a, b, c, h=1, i=8, j=None):
        assert get_args(sys._getframe()) == OrderedDict((
            ('a', a),
            ('b', b),
            ('c', c),
            ('h', h),
            ('i', i),
            ('j', j),
        ))

    def k(a, b, c, d=5, e=12, *args, **kwargs):
        assert get_args(sys._getframe()) == OrderedDict((
            ('a', a),
            ('b', b),
            ('c', c),
            ('d', d),
            ('e', e),
            ('*args', args),
            ('**kwargs', kwargs)
        ))

    def l(a, b, c, d=5, e=12, *args, h=1, i=8, j=None):
        assert get_args(sys._getframe()) == OrderedDict((
            ('a', a),
            ('b', b),
            ('c', c),
            ('d', d),
            ('e', e),
            ('*args', args),
            ('h', h),
            ('i', i),
            ('j', j),
        ))

    def m(a, b, c, d=5, e=12, h=1, i=8, j=None):
        assert get_args(sys._getframe()) == OrderedDict((
            ('a', a),
            ('b', b),
            ('c', c),
            ('d', d),
            ('e', e),
            ('h', h),
            ('i', i),
            ('j', j),
        ))

    f(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, m=13, n=14, o=15)
    f(1, 2, 3, 4, 5, 6, 7, 8, 9, h=10, i=11, j=12, m=13, n=14, o=15)
    g(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, m=13, n=14, o=15)
    g(1, 2, 3, 4, 5, 6, 7, 8, 9, h=10, i=11, j=12, m=13, n=14, o=15)
    h(1, 2, 3, 10, 11, 12, m=13, n=14, o=15)
    h(1, 2, 3, h=10, i=11, j=12, m=13, n=14, o=15)
    i(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)
    i(1, 2, 3, 4, 5, 6, 7, 8, 9, h=10, i=11, j=12)
    j(1, 2, 3, 10, 11, 12)
    j(1, 2, 3, h=10, i=11, j=12)
    k(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, m=13, n=14, o=15)
    k(1, 2, 3, 4, 5, 6, 7, 8, 9, h=10, i=11, j=12, m=13, n=14, o=15)
    l(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)
    l(1, 2, 3, 4, 5, 6, 7, 8, 9, h=10, i=11, j=12)
    m(1, 2, 3, 4, 5, 10, 11, 12)
    m(1, 2, 3, 4, 5, h=10, i=11, j=12)
'''
    )
