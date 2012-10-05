#!/usr/bin/env python
from flask import Flask
from werkzeug.debug import DebuggedApplication
import logging
from w import w
app = Flask(__name__)


@app.route("/")
def _():
    1 / 0
    return "Hello World!"

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


app.wsgi_app = w(app.wsgi_app)
app.run(debug=True, port=1984, use_debugger=False, use_reloader=False)
