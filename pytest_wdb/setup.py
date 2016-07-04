from setuptools import setup

setup(
    name="pytest_wdb",
    version='0.4.0',
    author="Florian Mounier @ kozea",
    author_email="florian.mounier@kozea.fr",
    url="http://github.com/Kozea/wdb",
    license='GPLv3',
    py_modules=['pytest_wdb'],
    install_requires=['wdb'],
    description="Trace pytest tests with wdb to halt on error with --wdb.",
    entry_points={
        'pytest11': [
            'pytest_wdb = pytest_wdb',
        ]
    },
)
