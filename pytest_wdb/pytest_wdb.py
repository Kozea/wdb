"""Wdb plugin for pytest."""
import wdb


def pytest_addoption(parser):
    parser.addoption("--wdb", action="store_true",
                     help="Trace tests with wdb to halt on error.")


def pytest_configure(config):
    if config.getoption('--wdb'):
        config.pluginmanager.register(Trace(), '_wdb')


class Trace(object):
    def pytest_runtest_call(self, item):
        testfunction = item.obj
        if item._isyieldedfunction():
            with wdb.trace():
                testfunction(*item._args)
        else:
            funcargs = item.funcargs
            testargs = {}
            for arg in item._fixtureinfo.argnames:
                testargs[arg] = funcargs[arg]
            with wdb.trace():
                testfunction(**testargs)
