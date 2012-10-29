#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
W debugger
"""

from setuptools import setup, find_packages

VERSION = "0.1"


options = dict(
    name="w",
    version=VERSION,
    description="An improbable web debugger through WebSockets",
    long_description=__doc__,
    author="Kozea - Florian Mounier",
    author_email="florian.mounier@kozea.fr",
    license="BSD",
    platforms="Any",
    use_2to3=True,
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Topic :: Software Development :: Debuggers"])

setup(**options)
