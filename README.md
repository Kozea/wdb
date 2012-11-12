w
=

![](https://raw.github.com/Kozea/w/master/w.png)

Description
-----------

**w** is as for now a proof of concept of an independant web debugger for wsgi project (implemented as a wsgi middleware).

Unlike other web debuggers, **w** is based on the [python bdb debugger framework](http://docs.python.org/2/library/bdb.html). (The one used by [pdb](http://docs.python.org/2/library/pdb.html))

This allows step by step debugging during the rendering of the page as well as exception inspection in the very state the exception occured.


How is it possible ?
--------------------

*WebSockets*! 
All debug information between web page and web server transits throught a websocket opened on a random port.
Server request processing is blocked by the websocket and then resumed when the debugging is over.


Warning
-------

This is still far from working perfectly, it has a lot of known issues and can easily break your application but the page debugging does work.

*Random disclaimer warning*

This python thing will probably eat your cat.


Instalation:
------------

```
    $ pip install w
```

Usage
-----

To try it you can simply run the `run.py` script which is a flask application which will be accessible at <http://localhost:1984/>.

To try it on another wsgi application, use the `W` middleware:

```python
    from w import W
    wsgi_app = Whathever_wsgi_server_lib()
    my_app = W(wsgi_app)
    my_app.serve_forever()
```

Using flask:

```python
    from w import W
    app = Flask(__name__)
    app.wsgi_app = W(app.wsgi_app)
    app.run()
```

You can now put some breakpoint in a request code:

```python
    do_something()
    W.tf  # Will break here
    return
```


Author
------

[Florian Mounier](http://github.com/paradoxxxzero) @ [Kozea](http://kozea.fr/)


Licence
-------

This library is licensed under GPLv3

w - An improbable web debugger through WebSockets


    w Copyright (C) 2012  Florian Mounier, Kozea

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
