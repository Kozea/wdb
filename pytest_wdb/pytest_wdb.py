"""Wdb plugin for pytest."""
import wdb


def pytest_addoption(parser):
    parser.addoption("--wdb", action="store_true",
                     help="Trace tests with wdb to halt on error.")


def pytest_configure(config):
    if config.getoption('--wdb'):
        config.pluginmanager.register(Trace(), '_wdb')
        config.pluginmanager.unregister(name='pdb')


class Trace(object):
    def pytest_pyfunc_call(self, pyfuncitem):
        testfunction = pyfuncitem.obj
        if pyfuncitem._isyieldedfunction():
            with wdb.trace():
                testfunction(*pyfuncitem._args)
        else:
            funcargs = pyfuncitem.funcargs
            testargs = {}
            for arg in pyfuncitem._fixtureinfo.argnames:
                testargs[arg] = funcargs[arg]
            with wdb.trace():
                testfunction(**testargs)

        # Avoid multiple test call
        return True
