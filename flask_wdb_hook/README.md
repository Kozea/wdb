# Flask WDB Hook
## Replace flask werkzeug debugger with wdb

[![](https://raw.github.com/Kozea/wdb/master/flask_wdb_hook/demo.gif)](https://raw.github.com/Kozea/wdb/master/flask_wdb_hook/demo.gif)


### Installation

```bash
    $ sudo pip install flask-wdb-hook
    $ export FLASK_WDB=1
```

### How does it work

This package only install a pth file in the site-packages directory which calls:
```python
import wdb; \
from wdb.ext import WdbMiddleware; \
from werkzeug import debug; \
debug.DebuggedApplication = WdbMiddleware  # This is so much a hack
```

As pth files contain either import path or python import statement, we abuse the import evaluation to patch the werkzeug debugger in the same statement.

Et voilà.
