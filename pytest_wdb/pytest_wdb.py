"""Wdb plugin for pytest."""
import wdb


def pytest_addoption(parser):
    parser.addoption(
        "--wdb",
        action="store_true",
        help="Trace tests with wdb to halt on error.",
    )


def pytest_configure(config):
    if config.option.wdb:
        config.pluginmanager.register(Trace(), '_wdb')
        config.pluginmanager.unregister(name='pdb')


class Trace(object):
    def pytest_collection_modifyitems(config, items):
        for item in items:
            item.obj = wdb.with_trace(item.obj)
