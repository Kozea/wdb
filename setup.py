#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
wdb
"""

from setuptools import setup, find_packages

VERSION = "0.9"


options = dict(
    name="wdb",
    version=VERSION,
    description="An improbable web debugger through WebSockets",
    long_description="See http://github.com/Kozea/wdb",
    author="Florian Mounier @ kozea",
    author_email="florian.mounier@kozea.fr",
    url="http://github.com/Kozea/wdb",
    license="GPLv3",
    platforms="Any",
    packages=find_packages(),
    install_requires=["log_colorizer", "jedi"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development :: Debuggers"])

setup(**options)
