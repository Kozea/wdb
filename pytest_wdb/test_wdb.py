# -*- coding: utf-8 -*-

import pytest
pytest_plugins = 'pytester',


def test_ok(testdir):
    testdir.makepyfile('''
        def test_run():
            print('Test has been run')
    ''')
    result = testdir.runpytest('--wdb')
    result.stdout.fnmatch_lines([
        'plugins:*wdb'
    ])
    assert result.ret == 0


def test_ok_run_once(testdir):
    testdir.makepyfile('''
        def test_run():
            print('Test has been run')
    ''')

    result = testdir.runpytest('--wdb', '-s')
    assert len([line for line in result.stdout.lines
                if line == 'test_ok_run_once.py Test has been run']) == 1
    assert result.ret == 0


# Todo implement fake wdb server

def test_fail_run_once(testdir):
    testdir.makepyfile('''
        def test_run():
            print('Test has been run')
            assert 0
    ''')

    result = testdir.runpytest('--wdb', '-s')
    assert len([line for line in result.stdout.lines
                if line == 'test_fail_run_once.py Test has been run']) == 1
    assert result.ret == 1


def test_error_run_once(testdir):
    testdir.makepyfile('''
        def test_run():
            print('Test has been run')
            1/0
    ''')

    result = testdir.runpytest('--wdb', '-s')
    assert len([line for line in result.stdout.lines
                if line == 'test_error_run_once.py Test has been run']) == 1
    assert result.ret == 1
