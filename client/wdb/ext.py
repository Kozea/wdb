# *-* coding: utf-8 *-*
# This file is part of wdb
#
# wdb Copyright (c) 2012-2016  Florian Mounier, Kozea
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from . import (
    trace,
    start_trace,
    stop_trace,
    set_trace,
    Wdb,
    WEB_SERVER,
    WEB_PORT,
)
from .ui import dump
from ._compat import to_bytes, escape, logger, TCPServer

import traceback
from threading import current_thread
from uuid import uuid4
import sys

log = logger(__name__)
_exc_cache = {}


def _patch_tcpserver():
    """
    Patch shutdown_request to open blocking interaction after the end of the
    request
    """
    shutdown_request = TCPServer.shutdown_request

    def shutdown_request_patched(*args, **kwargs):
        thread = current_thread()
        shutdown_request(*args, **kwargs)
        if thread in _exc_cache:
            post_mortem_interaction(*_exc_cache.pop(thread))

    TCPServer.shutdown_request = shutdown_request_patched


def post_mortem_interaction(uuid, exc_info):
    wdb = Wdb.get(force_uuid=uuid)
    type_, value, tb = exc_info
    frame = None
    _value = value
    if not isinstance(_value, BaseException):
        _value = type_(value)

    wdb.obj_cache[id(exc_info)] = exc_info
    wdb.extra_vars['__exception__'] = exc_info
    exception = type_.__name__
    exception_description = str(value) + ' [POST MORTEM]'
    init = 'Echo|%s' % dump(
        {
            'for': '__exception__',
            'val': escape('%s: %s') % (exception, exception_description),
        }
    )

    wdb.interaction(
        frame,
        tb,
        exception,
        exception_description,
        init=init,
        iframe_mode=True,
        timeout=3,
    )


def _handle_off(silent=False):
    if not silent:
        log.exception('Exception with wdb off')

    uuid = str(uuid4())
    _exc_cache[current_thread()] = (uuid, sys.exc_info())

    web_url = 'http://%s:%d/pm/session/%s' % (
        WEB_SERVER or 'localhost',
        WEB_PORT or 1984,
        uuid,
    )
    return to_bytes(
        '''<!DOCTYPE html>
        <html>
            <head>
                <title>WDB Post Mortem</title>
                <!--
                    %s
                -->
                <style>
                  html, body, iframe {
                    margin: 0;
                    padding: 0;
                    width: 100%%;
                    height: 100%%;
                    border: none;
                    overflow: hidden;
                    display: block;
                  }
                </style>
                <script>
                    addEventListener("message", function (e) {
                        if (e.data == 'activate') {
                            var request = new XMLHttpRequest();
                            request.open('GET', '/__wdb/on', true);
                            request.onload = function() {
                                location.reload(true);
                            }
                            request.send();
                        }
                    }, false);
                </script>
            </head>
            <body>
                <iframe
                    src="%s"
                    id="wdbframe">
                </iframe>
            </body>
        </html>
    '''
        % (traceback.format_exc(), web_url)
    )


class WdbMiddleware(object):
    def __init__(self, app, start_disabled=False):
        _patch_tcpserver()
        self.app = app
        Wdb.enabled = not start_disabled

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        if path == '/__wdb/on':
            # Enable wdb
            Wdb.enabled = True
            start_response('200 OK', [('Content-Type', 'text/html')])
            return (to_bytes('Wdb is now on'),)

        if path == '/__wdb/shell':

            def f():
                # Enable wdb
                wdb = Wdb.get()
                Wdb.enabled = True
                start_response(
                    '200 OK',
                    [('Content-Type', 'text/html'), ('X-Thing', wdb.uuid)],
                )
                yield to_bytes(' ' * 4096)
                wdb = set_trace()
                wdb.die()
                yield to_bytes('Exited')

            return f()
        if Wdb.enabled:

            def trace_wsgi(environ, start_response):
                wdb = Wdb.get()
                wdb.closed = False
                appiter = None
                try:
                    with trace(close_on_exit=True, under=self.app):
                        appiter = self.app(environ, start_response)
                        for item in appiter:
                            yield item
                except Exception:
                    exc_info = sys.exc_info()
                    try:
                        start_response(
                            '500 INTERNAL SERVER ERROR',
                            [('Content-Type', 'text/html')],
                        )
                    except AssertionError:
                        log.exception(
                            'Exception with wdb off and headers already set',
                            exc_info=exc_info,
                        )
                        yield '\n'.join(
                            traceback.format_exception(*exc_info)
                        ).replace('\n', '\n<br>\n').encode('utf-8')
                    else:
                        yield _handle_off()
                finally:
                    hasattr(appiter, 'close') and appiter.close()
                wdb.closed = False

            return trace_wsgi(environ, start_response)

        def catch(environ, start_response):
            appiter = None

            try:
                appiter = self.app(environ, start_response)
                for item in appiter:
                    yield item
            except Exception:
                exc_info = sys.exc_info()
                try:
                    start_response(
                        '500 INTERNAL SERVER ERROR',
                        [('Content-Type', 'text/html')],
                    )
                except AssertionError:
                    log.exception(
                        'Exception with wdb off and headers already set',
                        exc_info=exc_info,
                    )
                    yield '\n'.join(
                        traceback.format_exception(*exc_info)
                    ).replace('\n', '\n<br>\n').encode('utf-8')
                else:
                    yield _handle_off()
            finally:
                # Close set_trace debuggers
                stop_trace(close_on_exit=True)
                hasattr(appiter, 'close') and appiter.close()

        return catch(environ, start_response)


def wdb_tornado(application, start_disabled=False):
    from tornado.web import (
        RequestHandler,
        ErrorHandler,
        HTTPError,
        StaticFileHandler,
    )
    from tornado.gen import coroutine

    Wdb.enabled = not start_disabled

    class WdbOn(RequestHandler):
        def get(self):
            Wdb.enabled = True
            self.write('Wdb is now on')

    class WdbOff(RequestHandler):
        def get(self):
            Wdb.enabled = False
            self.write('Wdb is now off')

    application.add_handlers(
        r'.*', ((r'/__wdb/on', WdbOn), (r'/__wdb/off', WdbOff))
    )
    old_execute = RequestHandler._execute
    under = getattr(RequestHandler._execute, '__wrapped__', None)

    @coroutine
    def _wdb_execute(*args, **kwargs):
        from wdb import trace, Wdb

        if Wdb.enabled:
            wdb = Wdb.get()
            wdb.closed = False  # Activate request ignores

        interesting = True
        if len(args) > 0 and isinstance(args[0], ErrorHandler):
            interesting = False
        elif (
            len(args) > 2
            and isinstance(args[0], StaticFileHandler)
            and args[2] == 'favicon.ico'
        ):
            interesting = False

        if Wdb.enabled and interesting:
            with trace(close_on_exit=True, under=under):
                old_execute(*args, **kwargs)
        else:
            old_execute(*args, **kwargs)
            # Close set_trace debuggers
            stop_trace(close_on_exit=True)

        if Wdb.enabled:
            # Reset closed state
            wdb.closed = False

    RequestHandler._execute = _wdb_execute

    def _wdb_error_writter(self, status_code, **kwargs):
        silent = False
        ex = kwargs.get('exc_info')
        if ex:
            silent = issubclass(ex[0], HTTPError)
        self.finish(_handle_off(silent=silent))
        post_mortem_interaction(*_exc_cache.pop(current_thread()))

    RequestHandler.write_error = _wdb_error_writter


def add_w_builtin():
    class w(object):
        """Global shortcuts"""

        @property
        def tf(self):
            set_trace(sys._getframe().f_back)

        @property
        def start(self):
            start_trace(sys._getframe().f_back)

        @property
        def stop(self):
            stop_trace(sys._getframe().f_back)

        @property
        def trace(self):
            trace(sys._getframe().f_back)

    __builtins__['w'] = w()


def patch_werkzeug():
    """Replace werkzeug debug middleware"""
    try:
        from werkzeug import debug
    except ImportError:
        return
    debug.DebuggedApplication = WdbMiddleware
