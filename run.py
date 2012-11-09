#!/usr/bin/env python
from flask import Flask
import logging
from w import W
app = Flask(__name__)


def make_error():
    import whatever


def relay_error():
    make_error()


def bad_recur(n):
    1 / n
    return bad_recur(n - 1)


@app.route("/ok")
def good_function():
    a = 2
    return "It's working" * a


@app.route("/")
def bad_function():
    a = 2
    b = -2
    c = 1 / (a + b) < 0  # <strong> Err
    print c <b> a
    relay_error()
    return "Hello World!"


@app.route("/wtf/error")
def wtf_error():
    W.tf
    a = 2
    a / 0
    return 12


@app.route("/wtf")
def wtf():
    a = 12
    b = 21
    c = a / b
    W.tf
    d = a - 2
    e = b + a - c + d
    return 'OK! %d' % e


@app.route("/long")
def long_trace():
    return bad_recur(10)


@app.route("/gen")
def generator():

    def bad_gen(n):
        for i in reversed(range(n)):
            yield 1 / i

    return ''.join(bad_gen(10))


@app.route("/gen2")
def comprehension_generator():
    return ''.join((1 / i for i in reversed(range(10))))


@app.route("/lambda")
def lambda_():
    return ''.join(map(lambda x: 1 / x, reversed(range(10))))


from log_colorizer import make_colored_stream_handler
handler = make_colored_stream_handler()
app.logger.handlers = []
app.logger.addHandler(handler)
import werkzeug
werkzeug._internal._log('debug', '<-- I am with stupid')
logging.getLogger('werkzeug').handlers = []
logging.getLogger('werkzeug').addHandler(handler)
handler.setLevel(getattr(logging, 'DEBUG'))
app.logger.setLevel(getattr(logging, 'DEBUG'))
logging.getLogger('werkzeug').setLevel(
    getattr(logging, 'DEBUG'))

try:
    import wsreload
except ImportError:
    app.logger.debug('wsreload not found')
else:
    url = "http://l:1984/*"

    def log(httpserver):
        app.logger.debug('WSReloaded after server restart')
    wsreload.monkey_patch_http_server({'url': url}, callback=log)
    app.logger.debug('HTTPServer monkey patched for url %s' % url)

app.wsgi_app = W(app.wsgi_app)
app.run(debug=True, host='0.0.0.0', port=1984, use_debugger=False, use_reloader=True, threaded=False)
# 80chars 80chars 80chars 80chars 80chars 80chars 80chars 80chars 80chars 80char
