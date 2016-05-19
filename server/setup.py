#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
wdb.server
"""
import os
import re
import sys
from setuptools import setup

ROOT = os.path.dirname(__file__)
with open(os.path.join(ROOT, 'wdb_server', '__init__.py')) as fd:
    __version__ = re.search("__version__ = '([^']+)'", fd.read()).group(1)

requires = [
    "wdb==%s" % __version__, "tornado>=4.2",
    "filemagic>=1.6", "psutil>=2.1", 'tornado_systemd']
if sys.platform == 'linux':
    requires.append('pyinotify')

options = dict(
    name="wdb.server",
    version=__version__,
    description="An improbable web debugger through WebSockets (server)",
    long_description="See http://github.com/Kozea/wdb",
    author="Florian Mounier @ kozea",
    author_email="florian.mounier@kozea.fr",
    url="http://github.com/Kozea/wdb",
    license="GPLv3",
    platforms="Any",
    scripts=['wdb.server.py'],
    packages=['wdb_server'],
    install_requires=requires,
    package_data={
        'wdb_server': [
            'static/libs/material-design-lite/*',
            'static/stylesheets/*',
            'static/img/*.png',
            'static/javascripts/wdb/*.min.js',
            'templates/*.html'
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development :: Debuggers"])

setup(**options)
