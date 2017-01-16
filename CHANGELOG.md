3.1.0
=====

* Finally quiet uncompyle6
* Change default behavior for wdb script/__main__ now doesn't trace script by default but implement sys excepthook instead. Use --trace for old behavior.
* Dont fail out when ran under say a C-based WSGIHandler #87, #88 and Atomically set importmagic to avoid stampede #89 thanks @akatrevorjay
* Add patch_werkzeug method for use with hook

3.0.7
=====

* Add prompt ctrl+up/down command to include surrounding history
* Prevent prompt autofocus when there is a selection
* Avoid crash on empty code filename
* Fix python 3 kwonly keyword args
* Escape and linkify call/return args


3.0.6
=====

* Greyscale while working (The spinner might be too subtle)


3.0.5
=====

 * Add --show-filename option to show filename in session list (thanks @wong2)
 * Support msys2 (thanks @manuelnaranjo)

3.0.4
=====

 * Fix long subtitle style (thanks @wong2)
 * Fix wdb-lite setup.py
 * Use release script

3.0.1
=====

 * Fix double evaluation
 * Don't send cursor position to external editor open when holding shift key


3.0.0
=====

 * A whole new material design lite interface (a bit responsive)
 * Clickable icons instead of hotkeys only
 * Visual distinction between stepping, post_mortem and shell
 * An actually readable help (you can get by clicking on the help icons)
 * A code mirror prompt with syntaxic coloration and more classic completion
 * New commands (open current file in external editor, respawn current process...)
 * A far better post mortem interaction when using ext and wdb is disabled.
 * `importmagic` suggestions on NameError
 * Use of `uncompyle6` to get python source when only byte-code is available


2.1.0
=====

  * New completion mechanism, should complete a lot better
  * Experimental object tree search (`.f` command) to look for a key or a value condition in an object
  * Media display in debugger (`.i` command)
  * New diff function to print differences between string / obj / files (`.x` command)
  * Timing for expression evaluation (remote and local)
  * Prompt exception inspection (click on it)
  * A new shell mode and an executable `wdb`
  * A new multiline prompt mode triggered by `[ctrl]` + `[enter]`
  * And a lot of bug fixes


2.0.0
=====

 * Source syntax highlighting
 * Visual breakpoints
 * Interactive code completion using [jedi](http://jedi.jedidjah.ch/)
 * Persistent breakpoints
 * Deep objects inspection using mouse
 * Multithreading / Multiprocessing support
 * Remote debugging
 * Watch expressions
 * In debugger code edition
 * Popular web servers integration to break on error
 * In exception breaking during trace (not post-mortem) in contrary to the werkzeug debugger for instance
 * Breaking in currently running programs through code injection (on supported systems)
