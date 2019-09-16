# 3.3.0

- Fix crash on startup
- Upgrade node dependencies
- Pin tornado version to 5.x.x

# 3.2.5

- Fix bad horizontal scrolling in case of long strings and on firefox.

# 3.2.4

- Merged #117 (thanks @akalipetis):
- Fix crashes when websockets closed prematurely
- Add a base class to handle new connection verification
- Fix protocol interpolation in CoffeeScript

  # 3.2.3

- Make websockets work over HTTPS #113 (thanks @akalipetis)
- Document logging configuration (thanks @ptim)

  # 3.2.2

- Don't crash on version request failure and lower the timeouts. Fix #112

  # 3.2.1

- Fix some unicode handling in exception display. Fix #106

  # 3.2.0

- Tornado 5 compatibility

  # 3.1.10

- Force tornado < 5. This is the last release with pre tornado 5 compat.

  # 3.1.9

- Replace filemagic with python-magic and fix dependencies

  # 3.1.8

- Prevent uncompyle crash on unknown python version

  # 3.1.7

- Minor dependency upgrade (importmagic -> importmagic3)

  # 3.1.6

- Resolve NameError problem. Fix #101
- Fix prompt scroll. Fix #103
- Code style with yapf

  # 3.1.5

- Fix websocket send method. . Make it work with tornado 4.5. Fix #97

  # 3.1.4

- Use setuptools to set the **version**. Fix #96

  # 3.1.3

- Don't execute suggestions when timeout is not available (windows/threads) and when it's not asked manually. Should fix #94 or at least work around it.

  # 3.1.2

- Remove wheel to prevent pyinotify install by accident. #91 #78

  # 3.1.0

- Finally quiet uncompyle6
- Change default behavior for wdb script/**main** now doesn't trace script by default but implement sys excepthook instead. Use --trace for old behavior.
- Dont fail out when ran under say a C-based WSGIHandler #87, #88 and Atomically set importmagic to avoid stampede #89 thanks @akatrevorjay
- Add patch_werkzeug method for use with hook

  # 3.0.7

- Add prompt ctrl+up/down command to include surrounding history
- Prevent prompt autofocus when there is a selection
- Avoid crash on empty code filename
- Fix python 3 kwonly keyword args
- Escape and linkify call/return args

# 3.0.6

- Greyscale while working (The spinner might be too subtle)

# 3.0.5

- Add --show-filename option to show filename in session list (thanks @wong2)
- Support msys2 (thanks @manuelnaranjo)

  # 3.0.4

- Fix long subtitle style (thanks @wong2)
- Fix wdb-lite setup.py
- Use release script

  # 3.0.1

- Fix double evaluation
- Don't send cursor position to external editor open when holding shift key

# 3.0.0

- A whole new material design lite interface (a bit responsive)
- Clickable icons instead of hotkeys only
- Visual distinction between stepping, post_mortem and shell
- An actually readable help (you can get by clicking on the help icons)
- A code mirror prompt with syntaxic coloration and more classic completion
- New commands (open current file in external editor, respawn current process...)
- A far better post mortem interaction when using ext and wdb is disabled.
- `importmagic` suggestions on NameError
- Use of `uncompyle6` to get python source when only byte-code is available

# 2.1.0

- New completion mechanism, should complete a lot better
- Experimental object tree search (`.f` command) to look for a key or a value condition in an object
- Media display in debugger (`.i` command)
- New diff function to print differences between string / obj / files (`.x` command)
- Timing for expression evaluation (remote and local)
- Prompt exception inspection (click on it)
- A new shell mode and an executable `wdb`
- A new multiline prompt mode triggered by `[ctrl]` + `[enter]`
- And a lot of bug fixes

# 2.0.0

- Source syntax highlighting
- Visual breakpoints
- Interactive code completion using [jedi](http://jedi.jedidjah.ch/)
- Persistent breakpoints
- Deep objects inspection using mouse
- Multithreading / Multiprocessing support
- Remote debugging
- Watch expressions
- In debugger code edition
- Popular web servers integration to break on error
- In exception breaking during trace (not post-mortem) in contrary to the werkzeug debugger for instance
- Breaking in currently running programs through code injection (on supported systems)
