#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
wdb
"""
import os
import re
from setuptools import setup

ROOT = os.path.dirname(__file__)
with open(os.path.join(ROOT, 'wdb', '__init__.py')) as fd:
    __version__ = re.search("__version__ = '([^']+)'", fd.read()).group(1)

options = dict(
    name="wdb",
    version=__version__,
    description="An improbable web debugger through WebSockets (client only)",
    long_description="See http://github.com/Kozea/wdb",
    author="Florian Mounier @ kozea",
    author_email="florian.mounier@kozea.fr",
    url="http://github.com/Kozea/wdb",
    license="GPLv3",
    platforms="Any",
    packages=['wdb'],
    install_requires=["log_colorizer>=1.6", "jedi>=0.8.0"],
    package_data={
        'wdb': [
            'res/*'
        ]
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
