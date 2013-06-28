#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
wdb
"""

from setuptools import setup, find_packages

VERSION = "1.0.1"


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
    scripts=['wdb.server.py'],
    packages=find_packages(),
    install_requires=["tornado", "log_colorizer", "jedi"],
    package_data={
        'wdb_server': [
            'static/fonts/*',
            'static/stylesheets/*',
            'static/javascripts/*.js',
            'static/javascripts/codemirror-3.11/lib/codemirror.js',
            'static/javascripts/codemirror-3.11/lib/codemirror.css',
            'static/javascripts/codemirror-3.11/theme/tomorrow.css',
            'static/javascripts/codemirror-3.11/addon/dialog/dialog.css',
            'static/javascripts/codemirror-3.11/addon/runmode/runmode.js',
            'static/javascripts/codemirror-3.11/addon/search/search.js',
            'static/javascripts/codemirror-3.11/addon/search/searchcursor.js',
            'static/javascripts/codemirror-3.11/addon/dialog/dialog.js',
            'static/javascripts/codemirror-3.11/mode/javascript/javascript.js',
            'static/javascripts/codemirror-3.11/mode/python/python.js',
            'static/javascripts/codemirror-3.11/mode/jinja2/jinja2.js',
            'templates/*.html'
        ],
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
