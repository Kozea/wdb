#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
 W
"""

from setuptools import setup, find_packages

VERSION = "0.2"


options = dict(
    name="w",
    version=VERSION,
    description="An improbable web debugger through WebSockets",
    long_description="See http://github.com/Kozea/w",
    author="Florian Mounier @ kozea",
    author_email="florian.mounier@kozea.fr",
    url="http://github.com/Kozea/w",
    license="GPLv3",
    platforms="Any",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Topic :: Software Development :: Debuggers"])

setup(**options)
