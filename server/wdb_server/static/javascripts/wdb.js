var History, Interpreter, Log, Prompt, Source, Switch, Traceback, Watchers, Wdb, Websocket, help,
  extend = function(child, parent) { for (var key in parent) { if (hasProp.call(parent, key)) child[key] = parent[key]; } function ctor() { this.constructor = child; } ctor.prototype = parent.prototype; child.prototype = new ctor(); child.__super__ = parent.prototype; return child; },
  hasProp = {}.hasOwnProperty,
  indexOf = [].indexOf || function(item) { for (var i = 0, l = this.length; i < l; i++) { if (i in this && this[i] === item) return i; } return -1; };

if (!String.prototype.startsWith) {
  String.prototype.startsWith = function(searchString, position) {
    position = position || 0;
    return this.substr(position, searchString.length) === searchString;
  };
}

if (!document.createElement('dialog').showModal) {
  $(function() {
    $('head').append($('<script>', {
      src: 'https://cdnjs.cloudflare.com/' + 'ajax/libs/dialog-polyfill/0.4.3/dialog-polyfill.min.js'
    }));
    return $('head').append($('<link>', {
      rel: 'stylesheet',
      href: 'https://' + 'cdnjs.cloudflare.com/ajax/libs/dialog-polyfill/0.4.3/' + 'dialog-polyfill.min.css'
    }));
  });
}

Log = (function() {
  function Log() {
    this.debug = $('body').attr('data-debug') || false;
  }

  Log.prototype.time = function() {
    var date;
    date = new Date();
    return ((date.getHours()) + ":" + (date.getMinutes()) + ":") + ((date.getSeconds()) + "." + (date.getMilliseconds()));
  };

  Log.prototype.log = function() {
    var log_args, name;
    if (this.debug) {
      name = "[" + this.constructor.name + "] (" + (this.time()) + ")";
      log_args = [name].concat(Array.prototype.slice.call(arguments, 0));
      return console.log.apply(console, log_args);
    }
  };

  Log.prototype.dbg = function() {
    var log_args, name;
    if (this.debug) {
      name = "[" + this.constructor.name + "] (" + (this.time()) + ")";
      log_args = [name].concat(Array.prototype.slice.call(arguments, 0));
      return console.debug.apply(console, log_args);
    }
  };

  Log.prototype.fail = function() {
    var log_args, name;
    name = this.constructor.name;
    log_args = [name].concat(Array.prototype.slice.call(arguments, 0));
    return console.error.apply(console, log_args);
  };

  return Log;

})();

Websocket = (function(superClass) {
  extend(Websocket, superClass);

  function Websocket(wdb, uuid) {
    var proto;
    this.wdb = wdb;
    Websocket.__super__.constructor.call(this);
    proto = document.location.protocol === "https:" ? "wss:" : "ws:";
    this.url = proto + "//" + document.location.host + "/websocket/" + uuid;
    this.log('Opening new socket', this.url);
    this.ws = new WebSocket(this.url);
    this.ws.onclose = this.close.bind(this);
    this.ws.onopen = this.open.bind(this);
    this.ws.onerror = this.error.bind(this);
    this.ws.onmessage = this.message.bind(this);
  }

  Websocket.prototype.close = function(m) {
    this.log("Closed", m);
    return this.wdb.die();
  };

  Websocket.prototype.error = function(m) {
    return this.fail("Error", m);
  };

  Websocket.prototype.open = function(m) {
    this.log("Open", m);
    return this.wdb.opening();
  };

  Websocket.prototype.message = function(m) {
    var cmd, data, message, pipe;
    message = m.data;
    pipe = message.indexOf('|');
    if (pipe > -1) {
      cmd = message.substr(0, pipe);
      data = JSON.parse(message.substr(pipe + 1));
    } else {
      cmd = message;
    }
    this.dbg(this.time(), '<-', message);
    cmd = cmd.toLowerCase();
    if (cmd in this.wdb) {
      return this.wdb[cmd.toLowerCase()](data);
    } else {
      return this.fail('Unknown command', cmd);
    }
  };

  Websocket.prototype.send = function(cmd, data) {
    var msg;
    if (data == null) {
      data = null;
    }
    if (data) {
      if (typeof data !== 'string') {
        data = JSON.stringify(data);
      }
      msg = cmd + "|" + data;
    } else {
      msg = cmd;
    }
    this.dbg('->', msg);
    return this.ws.send(msg);
  };

  return Websocket;

})(Log);

Source = (function(superClass) {
  extend(Source, superClass);

  function Source(wdb) {
    this.wdb = wdb;
    Source.__super__.constructor.call(this);
    this.$container = $('.source').on('mousedown', (function(_this) {
      return function(e) {
        if (!(e.which === 2 && _this.code_mirror.getOption('readOnly'))) {
          return;
        }
        return _this.code_mirror.setOption('readOnly', 'nocursor');
      };
    })(this)).on('mouseup', (function(_this) {
      return function(e) {
        if (e.which !== 2) {
          return;
        }
        _this.code_mirror.setOption('readOnly', true);
        return _this.wdb.paste_target(e);
      };
    })(this));
    this.code_mirror = CodeMirror((function(_this) {
      return function(elt) {
        _this.$code_mirror = $(elt);
        return _this.$container.prepend(elt);
      };
    })(this), {
      value: 'No active file',
      theme: 'material',
      readOnly: true,
      gutters: ['breaks', 'CodeMirror-linenumbers'],
      lineNumbers: true,
      extraKeys: {
        Esc: this.stop_edition.bind(this),
        'Ctrl-S': this.save.bind(this)
      }
    });
    this.code_mirror.on('gutterClick', this.gutter_click.bind(this));
    $(window).on('resize', this.size.bind(this));
    this.state = {
      fn: null,
      file: null,
      fun: null,
      lno: 0
    };
    this.fun_scope = null;
    this.footsteps = {};
    this.breakpoints = {};
  }

  Source.prototype.external = function(full) {
    var cursor, fn;
    if (full == null) {
      full = true;
    }
    cursor = this.code_mirror.getCursor();
    fn = "" + this.state.fn;
    if (full) {
      fn = fn + ":" + (cursor.line + 1) + ":" + (cursor.ch + 1);
    }
    return this.wdb.ws.send('External', fn);
  };

  Source.prototype.save = function() {
    var new_file;
    if (this.code_mirror.getOption('readOnly')) {
      return;
    }
    new_file = this.code_mirror.getValue();
    this.wdb.ws.send('Save', this.state.fn + "|" + new_file);
    return this.state.file = new_file;
  };

  Source.prototype.gutter_click = function(_, n) {
    return this.wdb.toggle_break(":" + (n + 1));
  };

  Source.prototype.clear_breakpoint = function(brk) {
    var base, name1;
    if ((base = this.breakpoints)[name1 = brk.fn] == null) {
      base[name1] = [];
    }
    if (indexOf.call(this.breakpoints[brk.fn], brk) >= 0) {
      this.breakpoints[brk.fn].splice(this.breakpoints[brk.fn].indexOf(brk));
    }
    if (brk.lno) {
      this.remove_mark(brk.lno);
      this.remove_class(brk.lno, 'ask-breakpoint');
      return this.remove_class(brk.lno, 'breakpoint');
    }
  };

  Source.prototype.ask_breakpoint = function(lno) {
    return this.add_class(lno, 'ask-breakpoint');
  };

  Source.prototype.set_breakpoint = function(brk) {
    var base, name1;
    if ((base = this.breakpoints)[name1 = brk.fn] == null) {
      base[name1] = [];
    }
    this.breakpoints[brk.fn].push(brk);
    return this.mark_breakpoint(brk);
  };

  Source.prototype.mark_breakpoint = function(brk) {
    if (brk.lno) {
      this.remove_class(brk.lno, 'ask-breakpoint');
      this.add_class(brk.lno, 'breakpoint');
      return this.add_mark(brk.lno, 'breakpoint', 'breaks', (brk.temporary ? '○' : '●'), this.brk_to_str(brk));
    }
  };

  Source.prototype.brk_to_str = function(brk) {
    var str;
    if (brk.temporary) {
      str = 'Temporary ';
    } else {
      str = '';
    }
    str += 'Breakpoint';
    if (brk.fun) {
      str += " On " + brk.fun;
    }
    if (brk.lno) {
      str += " At " + brk.lno;
    }
    if (brk.cond) {
      str += " If " + brk.cond;
    }
    return str;
  };

  Source.prototype.get_selection = function() {
    return this.code_mirror.getSelection().trim();
  };

  Source.prototype.get_breakpoint = function(n) {
    var base, brk, j, len, name1, ref;
    if ((base = this.breakpoints)[name1 = this.state.fn] == null) {
      base[name1] = [];
    }
    ref = this.breakpoints[this.state.fn];
    for (j = 0, len = ref.length; j < len; j++) {
      brk = ref[j];
      if (brk.lno === n) {
        return brk;
      }
    }
  };

  Source.prototype.add_class = function(lno, cls) {
    return this.code_mirror.addLineClass(lno - 1, 'background', cls);
  };

  Source.prototype.remove_class = function(lno, cls) {
    return this.code_mirror.removeLineClass(lno - 1, 'background', cls);
  };

  Source.prototype.add_mark = function(lno, cls, id, char, title) {
    return this.code_mirror.setGutterMarker(lno - 1, id, $('<div>', {
      "class": cls,
      title: title
    }).html(char).get(0));
  };

  Source.prototype.remove_mark = function(lno) {
    return this.code_mirror.setGutterMarker(lno - 1, 'breaks', null);
  };

  Source.prototype.stop_edition = function() {
    if (!this.code_mirror.getOption('readOnly')) {
      return this.toggle_edition();
    }
  };

  Source.prototype.toggle_edition = function() {
    var was_ro;
    was_ro = this.code_mirror.getOption('readOnly');
    this.code_mirror.setOption('readOnly', !was_ro);
    this.$code_mirror.toggleClass('rw', 'ro');
    this.wdb.print({
      "for": "Toggling edition",
      result: "Edit mode " + (was_ro ? 'on' : 'off')
    });
    if (!was_ro) {
      return this.code_mirror.setValue(this.state.file);
    }
  };

  Source.prototype.open = function(data, frame) {
    var new_state;
    new_state = {
      fn: data.name,
      file: data.file || frame.code,
      fun: frame["function"],
      lno: frame.lno,
      flno: frame.flno,
      llno: frame.llno
    };
    return this.set_state(new_state);
  };

  Source.prototype.set_state = function(new_state) {
    var base, brk, j, k, l, len, len1, lno, name1, o, ref, ref1, ref2, ref3, ref4, ref5, rescope, step;
    rescope = true;
    if (this.state.fn !== new_state.fn || this.state.file !== new_state.file) {
      this.code_mirror.setOption('mode', this.get_mode(new_state.fn));
      this.code_mirror.setValue(new_state.file);
      ref = this.breakpoints[new_state.fn] || [];
      for (j = 0, len = ref.length; j < len; j++) {
        brk = ref[j];
        this.mark_breakpoint(brk);
      }
    } else {
      if (this.state.fun !== new_state.fun) {
        if (this.state.fun !== '<module>') {
          this.remove_class(this.state.flno, 'ctx-top');
          for (lno = k = ref1 = this.state.flno, ref2 = this.state.llno; ref1 <= ref2 ? k <= ref2 : k >= ref2; lno = ref1 <= ref2 ? ++k : --k) {
            this.remove_class(lno, 'ctx');
          }
          this.remove_class(this.state.llno, 'ctx-bottom');
        }
      } else {
        rescope = false;
      }
    }
    this.state = new_state;
    this.code_mirror.clearGutter('CodeMirror-linenumbers');
    ref3 = this.footsteps[this.state.fn] || [];
    for (l = 0, len1 = ref3.length; l < len1; l++) {
      step = ref3[l];
      this.remove_class(step, 'highlighted');
      this.add_class(step, 'footstep');
    }
    if (rescope && this.state.fun !== '<module>') {
      this.add_class(this.state.flno, 'ctx-top');
      for (lno = o = ref4 = this.state.flno, ref5 = this.state.llno; ref4 <= ref5 ? o <= ref5 : o >= ref5; lno = ref4 <= ref5 ? ++o : --o) {
        this.add_class(lno, 'ctx');
      }
      this.add_class(this.state.llno, 'ctx-bottom');
    }
    this.add_class(this.state.lno, 'highlighted');
    this.add_mark(this.state.lno, 'highlighted', 'CodeMirror-linenumbers', '➤');
    if ((base = this.footsteps)[name1 = this.state.fn] == null) {
      base[name1] = [];
    }
    this.footsteps[this.state.fn].push(this.state.lno);
    this.code_mirror.scrollIntoView({
      line: this.state.lno,
      ch: 1
    }, this.$code_mirror.height() / 2);
    return this.code_mirror.refresh();
  };

  Source.prototype.get_mode = function(fn) {
    switch (fn.split('.').splice(-1)[0]) {
      case 'py':
        return 'python';
      case 'jinja2':
        return 'jinja2';
      case 'diff':
        return 'diff';
      default:
        return 'python';
    }
  };

  Source.prototype.focused = function() {
    return this.$code_mirror.hasClass('CodeMirror-focused');
  };

  Source.prototype.size = function() {
    this.$code_mirror.height(0);
    this.$code_mirror.height(this.$container.height());
    return this.code_mirror.refresh();
  };

  return Source;

})(Log);

History = (function(superClass) {
  extend(History, superClass);

  function History(prompt) {
    var e, error;
    this.prompt = prompt;
    History.__super__.constructor.call(this);
    this.index = -1;
    this.current = '';
    this.currentPos = CodeMirror.Pos(0, 0);
    this.oldIndex = null;
    this.originalIndex = null;
    this.overlay = null;
    try {
      this.history = JSON.parse(localStorage['history'] || '[]');
    } catch (error) {
      e = error;
      this.fail(e);
      this.history = [];
    }
    this.sessionIndexStart = this.history.filter(function(e) {
      return e.indexOf('.') !== 0;
    }).length;
  }

  History.prototype.up = function() {
    if (this.index === -1) {
      this.saveCurrent();
    }
    this.index = Math.min(this.history.length - 1, this.index + 1);
    return this.sync();
  };

  History.prototype.down = function() {
    this.index = Math.max(this.index - 1, -1);
    return this.sync();
  };

  History.prototype.saveCurrent = function() {
    this.current = this.prompt.get();
    return this.currentPos = this.prompt.code_mirror.getCursor();
  };

  History.prototype.sync = function() {
    if (this.index === -1) {
      this.prompt.set(this.current);
      return this.prompt.code_mirror.setCursor(this.currentPos);
    } else {
      this.prompt.set(this.history[this.index]);
      return this.prompt.code_mirror.setCursor(this.prompt.code_mirror.lineCount(), 0);
    }
  };

  History.prototype.historize = function(snippet) {
    var index;
    if (!snippet) {
      return;
    }
    while ((index = this.history.indexOf(snippet)) !== -1) {
      this.history.splice(index, 1);
    }
    this.history.unshift(snippet);
    return localStorage && (localStorage['history'] = JSON.stringify(this.history));
  };

  History.prototype.reset = function() {
    this.index = -1;
    this.current = '';
    return this.currentPos = CodeMirror.Pos(0, 0);
  };

  History.prototype.clear = function() {
    this.history = [];
    this.sessionIndexStart = 0;
    return this.reset();
  };

  History.prototype.getOverlay = function(re) {
    return {
      token: function(stream) {
        var match;
        re.lastIndex = stream.pos;
        match = re.exec(stream.string);
        if (match && match.index === stream.pos) {
          stream.pos += match[0].length || 1;
          return "searching";
        } else if (match) {
          stream.pos = match.index;
        } else {
          stream.skipToEnd();
        }
      }
    };
  };

  History.prototype.searchPrev = function(val) {
    return this.searchNext(val, -1);
  };

  History.prototype.searchNext = function(val, step) {
    var re;
    if (step == null) {
      step = 1;
    }
    if (this.oldIndex == null) {
      this.oldIndex = this.index;
    }
    if (this.originalIndex == null) {
      this.originalIndex = this.index;
      if (this.index === -1) {
        this.saveCurrent();
      }
    }
    while (step === 1 && this.index < this.history.length || step === -1 && this.index > -1) {
      this.index += step;
      re = new RegExp("(" + (val.replace(/[\-\[\]\/\{\}\(\)\*\+\?\.\\\^\$\|]/g, "\\$&")) + ")", 'gi');
      if (re.test(this.history[this.index])) {
        this.lastResult = this.index;
        this.sync();
        (this.overlay != null) && this.prompt.code_mirror.removeOverlay(this.overlay, true);
        this.overlay = this.getOverlay(re);
        this.prompt.code_mirror.addOverlay(this.overlay);
        return true;
      }
    }
    return false;
  };

  History.prototype.commitSearch = function() {
    this.oldIndex = null;
    this.originalIndex = null;
    this.index = this.lastResult;
    return this.sync();
  };

  History.prototype.rollbackSearch = function() {
    this.oldIndex = null;
    if (this.originalIndex != null) {
      this.index = this.originalIndex;
    }
    this.originalIndex = null;
    (this.overlay != null) && this.prompt.code_mirror.removeOverlay(this.overlay, true);
    this.overlay = null;
    return this.sync();
  };

  History.prototype.resetSearch = function() {
    if (this.oldIndex != null) {
      this.index = this.oldIndex;
    }
    return this.oldIndex = null;
  };

  History.prototype.getSessionHistory = function() {
    return this.history.slice(0, this.history.length - this.sessionIndexStart);
  };

  History.prototype.getHistory = function(direction) {
    var begin, end;
    begin = 0;
    end = this.history.length - this.sessionIndexStart;
    if (direction === 'down') {
      end = this.index + 1;
    } else if (direction === 'up') {
      begin = this.index;
    }
    return this.history.slice(begin, end);
  };

  return History;

})(Log);

Traceback = (function(superClass) {
  extend(Traceback, superClass);

  function Traceback(wdb) {
    this.wdb = wdb;
    Traceback.__super__.constructor.call(this);
    this.$traceback = $('.traceback');
    this.$traceback.on('click', '.trace-line', this.select.bind(this));
  }

  Traceback.prototype.select = function(e) {
    var level;
    level = $(e.currentTarget).attr('data-level');
    this.wdb.select_trace(level);
    if ($('.mdl-layout__obfuscator').is('.is-visible')) {
      $('.mdl-layout').get(0).MaterialLayout.toggleDrawer();
    }
    return false;
  };

  Traceback.prototype.make_trace = function(trace) {
    var $primary, $tracebody, $traceline, brk, frame, j, k, len, len1, ref, results;
    this.clear();
    this.show();
    results = [];
    for (j = 0, len = trace.length; j < len; j++) {
      frame = trace[j];
      $traceline = $('<a>', {
        "class": 'trace-line ellipsis mdl-list__item mdl-list__item--three-line trace-' + frame.level
      }).attr('data-level', frame.level).attr('title', ("File \"" + frame.file + "\", line " + frame.lno + ", in " + frame["function"] + "\n") + ("    " + frame.code));
      ref = this.wdb.source.breakpoints[frame.file] || [];
      for (k = 0, len1 = ref.length; k < len1; k++) {
        brk = ref[k];
        if (!(brk.cond || brk.fun || brk.lno)) {
          $traceline.addClass('breakpoint');
          break;
        }
      }
      if (frame.current) {
        $traceline.addClass('real-selected');
      }
      $primary = $('<div>', {
        "class": 'mdl-list__item-primary-content'
      });
      $primary.append($('<div>', {
        "class": 'ellipsis'
      }).text(frame["function"]));
      $primary.append($('<div>', {
        "class": 'mdl-list__item-text-body'
      }).append($tracebody = $('<div>', {
        "class": 'ellipsis'
      })).append($('<div>', {
        "class": 'ellipsis'
      }).text(frame.file.split('/').slice(-1)[0] + ':' + frame.lno).prepend($('<i>', {
        "class": 'material-icons'
      }).text(this.get_fn_icon(frame.file)))));
      this.wdb.code($tracebody, frame.code, ['ellipsis']);
      $traceline.append($primary);
      results.push(this.$traceback.prepend($traceline));
    }
    return results;
  };

  Traceback.prototype.hide = function() {
    return this.$traceback.addClass('hidden');
  };

  Traceback.prototype.show = function() {
    return this.$traceback.removeClass('hidden');
  };

  Traceback.prototype.clear = function() {
    return this.$traceback.empty();
  };

  Traceback.prototype.get_fn_icon = function(fn) {
    if (!!~fn.indexOf('site-packages')) {
      return 'library_books';
    } else if (fn.startsWith(this.wdb.cwd) || fn[0] !== '/') {
      return 'star';
    } else if (fn.startsWith('/home/')) {
      return 'home';
    } else if (fn.startsWith('/usr/lib') && !!~fn.indexOf('/python')) {
      return 'lock';
    } else {
      return 'cloud';
    }
  };

  return Traceback;

})(Log);

Interpreter = (function(superClass) {
  extend(Interpreter, superClass);

  function Interpreter(wdb) {
    this.wdb = wdb;
    Interpreter.__super__.constructor.call(this);
    this.$terminal = $('.terminal').on('click', (function(_this) {
      return function() {
        if (!getSelection().toString()) {
          return _this.focus();
        }
      };
    })(this)).on('click', 'a.inspect', this.inspect.bind(this));
    this.$scrollback = $('.scrollback').on('click', '.short.close', this.short_open.bind(this)).on('click', '.short.open', this.short_close.bind(this)).on('click', '.toggle', this.toggle_visibility.bind(this));
  }

  Interpreter.prototype.scroll = function(direction) {
    if (direction == null) {
      direction = null;
    }
    if (direction) {
      this.$terminal.scrollTop(this.$terminal.scrollTop() + direction * this.$terminal.height());
      return;
    }
    return this.wdb.prompt.$container.get(0).scrollIntoView({
      behavior: "smooth"
    });
  };

  Interpreter.prototype.clear = function() {
    return this.$scrollback.empty();
  };

  Interpreter.prototype.write = function(elt) {
    return this.$scrollback.append(elt);
  };

  Interpreter.prototype.inspect = function(e) {
    return this.wdb.inspect($(e.currentTarget).attr('href'));
  };

  Interpreter.prototype.short_open = function(e) {
    return $(e.currentTarget).addClass('open').removeClass('close').next('.long').show('fast');
  };

  Interpreter.prototype.short_close = function(e) {
    return $(e.currentTarget).addClass('close').removeClass('open').next('.long').hide('fast');
  };

  Interpreter.prototype.toggle_visibility = function(e) {
    return $(e.currentTarget).add($(e.currentTarget).next()).toggleClass('closed', 'shown');
  };

  Interpreter.prototype.focus = function(e) {
    var scroll;
    scroll = this.$terminal.scrollTop();
    this.wdb.prompt.focus();
    return this.$terminal.scrollTop(scroll);
  };

  return Interpreter;

})(Log);

Prompt = (function(superClass) {
  extend(Prompt, superClass);

  function Prompt(wdb) {
    this.wdb = wdb;
    Prompt.__super__.constructor.call(this);
    this.$container = $('.prompt');
    this.history = new History(this);
    this.code_mirror = CodeMirror((function(_this) {
      return function(elt) {
        _this.$code_mirror = $(elt);
        return _this.$container.prepend(elt);
      };
    })(this), {
      value: '',
      theme: 'default',
      language: 'python',
      viewportMargin: Infinity,
      lineWrapping: true,
      autofocus: true,
      specialChars: /[\u0000-\u0019\u00a0\u00ad\u200b-\u200f\u2028\u2029\ufeff]/
    });
    this.code_mirror.on('changes', this.changes.bind(this));
    CodeMirror.registerHelper("hint", "jedi", (function(_this) {
      return function(cm, callback, options) {
        var cur, from, help, key, to, tok;
        cur = cm.getCursor();
        tok = cm.getTokenAt(cur);
        if (cm.getValue().startsWith('.') && cm.getValue().length === 2) {
          return;
        }
        from = CodeMirror.Pos(cur.line, tok.start);
        to = CodeMirror.Pos(cur.line, tok.end);
        if (cm.getValue() === '.') {
          callback({
            from: from,
            to: to,
            list: (function() {
              var ref, results;
              ref = {
                a: 'History',
                b: 'Break',
                c: 'Continue',
                d: 'Dump',
                e: 'Edition',
                f: 'Find',
                g: 'Clear',
                h: 'Help',
                i: 'Display',
                j: 'Jump',
                k: 'Clear',
                l: 'Breakpoints',
                m: 'Restart',
                n: 'Next',
                o: 'Open',
                q: 'Quit',
                r: 'Return',
                s: 'Step',
                t: 'Tbreak',
                u: 'Until',
                w: 'Watch',
                x: 'Diff',
                z: 'Unbreak'
              };
              results = [];
              for (key in ref) {
                if (!hasProp.call(ref, key)) continue;
                help = ref[key];
                results.push({
                  text: '.' + key,
                  displayText: "." + key + " <i>" + (this.leftpad('(' + help + ')', 14)) + "</i>  ",
                  render: function(elt, data, cur) {
                    return $(elt).html(cur.displayText);
                  }
                });
              }
              return results;
            }).call(_this)
          });
          return;
        }
        if (!options.completeSingle) {
          if (!tok.string.match(/[\w\.\(\[\{]/)) {
            return;
          }
        }
        _this.wdb.ws.send('Complete', {
          source: cm.getValue(),
          pos: _this.code_mirror.getRange({
            line: 0,
            ch: 0
          }, cur).length,
          line: cur.line + 1,
          column: cur.ch,
          manual: options.completeSingle
        });
        return _this.completion = {
          cur: cur,
          tok: tok,
          from: from,
          to: to,
          callback: callback
        };
      };
    })(this));
    this.code_mirror.addKeyMap({
      'Enter': this.newLineOrExecute.bind(this),
      'Up': this.history.up.bind(this.history),
      'Down': this.history.down.bind(this.history),
      'Ctrl-C': this.abort.bind(this),
      'Ctrl-D': (function(_this) {
        return function() {
          if (!_this.get()) {
            return _this.wdb.die();
          }
        };
      })(this),
      'Ctrl-F': function() {},
      'Ctrl-R': (function(_this) {
        return function() {
          return _this.searchBack();
        };
      })(this),
      'Ctrl-S': (function(_this) {
        return function() {
          return _this.searchBack(false);
        };
      })(this),
      'Ctrl-K': 'killLine',
      'Ctrl-L': this.wdb.cls.bind(this.wdb),
      'Ctrl-Enter': 'newlineAndIndent',
      'Alt-Backspace': 'delGroupBefore',
      'Ctrl-Space': this.triggerAutocomplete.bind(this),
      'Ctrl-Up': (function(_this) {
        return function() {
          return _this.insertHistory('up');
        };
      })(this),
      'Ctrl-Down': (function(_this) {
        return function() {
          return _this.insertHistory('down');
        };
      })(this),
      'PageUp': 'goLineUp',
      'PageDown': 'goLineDown',
      'PageDown': 'goLineDown',
      'Shift-PageUp': (function(_this) {
        return function() {
          return _this.wdb.interpreter.scroll(-1);
        };
      })(this),
      'Shift-PageDown': (function(_this) {
        return function() {
          return _this.wdb.interpreter.scroll(1);
        };
      })(this),
      'Tab': (function(_this) {
        return function(cm, options) {
          var cur, rng, spaces;
          cur = _this.code_mirror.getCursor();
          rng = _this.code_mirror.getRange({
            line: cur.line,
            ch: 0
          }, cur);
          if (rng.trim()) {
            return _this.triggerAutocomplete(cm, options);
          } else {
            spaces = Array(_this.code_mirror.getOption("indentUnit") + 1).join(" ");
            return _this.code_mirror.replaceSelection(spaces);
          }
        };
      })(this)
    });
    this.code_mirror.on('keyup', (function(_this) {
      return function(cm, e) {
        var ref;
        if (!cm.getValue()) {
          return;
        }
        if ((8 < (ref = e.keyCode) && ref < 42)) {
          return;
        }
        return CodeMirror.commands.autocomplete(cm, CodeMirror.hint.jedi, {
          async: true,
          completeSingle: false,
          extraKeys: {
            PageUp: 'goPageUp',
            PageDown: 'goPageDown',
            Home: 'goLineStartSmart',
            Up: function(cm, handle) {
              handle._dirty = true;
              return handle.moveFocus(-1);
            },
            Down: function(cm, handle) {
              handle._dirty = true;
              return handle.moveFocus(1);
            },
            Enter: function(cm, handle) {
              if (handle._dirty) {
                return handle.pick();
              } else {
                return _this.newLineOrExecute(cm);
              }
            },
            Right: function(cm, handle) {
              if (handle._dirty) {
                return handle.pick();
              } else {
                return CodeMirror.commands.goCharRight(cm);
              }
            },
            End: 'goLineEnd'
          }
        });
      };
    })(this));
  }

  Prompt.prototype.complete = function(data) {
    var completion, cur, hints, tok;
    if (data.completions && this.completion) {
      cur = this.completion.cur;
      tok = this.completion.tok;
      hints = {
        from: CodeMirror.Pos(cur.line, tok.start),
        to: CodeMirror.Pos(cur.line, tok.end),
        list: (function() {
          var j, len, ref, results;
          ref = data.completions;
          results = [];
          for (j = 0, len = ref.length; j < len; j++) {
            completion = ref[j];
            results.push({
              text: completion.base + completion.complete,
              from: CodeMirror.Pos(cur.line, cur.ch - completion.base.length),
              to: cur,
              _completion: completion,
              render: function(elt, data, cur) {
                var c, item;
                c = cur._completion;
                item = "<b>" + c.base + "</b>" + c.complete;
                return $(elt).html(item);
              }
            });
          }
          return results;
        })()
      };
      CodeMirror.on(hints, 'shown', (function(_this) {
        return function() {
          var cls;
          if (_this.code_mirror.state.completionActive.options.completeSingle) {
            cls = 'triggered';
          } else {
            cls = 'auto';
          }
          return $(_this.code_mirror.state.completionActive.widget.hints).addClass(cls);
        };
      })(this));
      this.completion.callback(hints);
      return;
    }
    if (data.imports) {
      return CodeMirror.commands.autocomplete(this.code_mirror, function(cm, options) {
        var imp;
        return {
          from: CodeMirror.Pos(0, 0),
          to: CodeMirror.Pos(0, 0),
          list: (function() {
            var j, len, ref, results;
            ref = data.imports;
            results = [];
            for (j = 0, len = ref.length; j < len; j++) {
              imp = ref[j];
              results.push({
                text: imp,
                from: CodeMirror.Pos(0, 0),
                to: CodeMirror.Pos(0, 0),
                render: function(elt, data, cur) {
                  var item;
                  item = "<em>" + cur.text + "</em>";
                  return $(elt).html(item);
                }
              });
            }
            return results;
          })()
        };
      }, {
        async: false,
        completeSingle: false
      });
    }
  };

  Prompt.prototype.triggerAutocomplete = function(cm, options) {
    return CodeMirror.commands.autocomplete(cm, CodeMirror.hint.jedi, {
      async: true,
      extraKeys: {
        Right: function(cm, handle) {
          return handle.pick();
        }
      }
    });
  };

  Prompt.prototype.newLineOrExecute = function(cm) {
    var snippet;
    snippet = cm.getValue().trim();
    if (!snippet) {
      return;
    }
    cm.setOption('readOnly', 'nocursor');
    this.$container.addClass('loading');
    return this.wdb.execute(snippet);
  };

  Prompt.prototype.focus = function() {
    return this.code_mirror.focus();
  };

  Prompt.prototype.focused = function() {
    return this.$code_mirror.hasClass('CodeMirror-focused');
  };

  Prompt.prototype.abort = function() {
    this.history.reset();
    return this.set('');
  };

  Prompt.prototype.ready = function(newline) {
    var snippet;
    if (newline == null) {
      newline = false;
    }
    if (newline) {
      this.code_mirror.execCommand('newlineAndIndent');
    } else {
      snippet = this.code_mirror.getValue().trim();
      this.history.historize(snippet);
      this.history.reset();
      this.set('');
    }
    return this.unlock();
  };

  Prompt.prototype.unlock = function() {
    this.$container.removeClass('loading');
    this.code_mirror.setOption('readOnly', false);
    return this.focus();
  };

  Prompt.prototype.get = function() {
    return this.code_mirror.getValue();
  };

  Prompt.prototype.set = function(val) {
    return this.code_mirror.setValue(val);
  };

  Prompt.prototype.leftpad = function(str, n, c) {
    var i, j, p, ref;
    if (c == null) {
      c = ' ';
    }
    p = n - str.length;
    for (i = j = 0, ref = p; 0 <= ref ? j <= ref : j >= ref; i = 0 <= ref ? ++j : --j) {
      str = c + str;
    }
    return str;
  };

  Prompt.prototype.searchBack = function(back) {
    var close;
    if (back == null) {
      back = true;
    }
    this.$code_mirror.addClass('extra-dialog');
    close = this.code_mirror.openDialog("<span class=\"search-dialog-title\">\n  Search " + (back ? 'backward' : 'forward') + ":\n</span>\n<input type=\"text\" style=\"width: 10em\" class=\"CodeMirror-search-field\"/>", (function(_this) {
      return function(val, e) {
        return _this.history.commitSearch();
      };
    })(this), {
      bottom: true,
      onInput: (function(_this) {
        return function(e, val, close) {
          if (!val) {
            return;
          }
          _this.history.resetSearch();
          return $('.CodeMirror-search-field').toggleClass('not-found', val && !_this.history[close.back ? 'searchNext' : 'searchPrev'](val));
        };
      })(this),
      onKeyDown: (function(_this) {
        return function(e, val, close) {
          if (e.keyCode === 82 && e.ctrlKey || e.keyCode === 83 && e.altKey) {
            close.back = true;
            $('.search-dialog-title').text('Search backward:');
            $('.CodeMirror-search-field').toggleClass('not-found', val && !_this.history.searchNext(val));
            e.preventDefault();
            e.stopPropagation();
          }
          if (e.keyCode === 83 && e.ctrlKey || e.keyCode === 82 && e.altKey) {
            close.back = false;
            $('.search-dialog-title').text('Search forward:');
            $('.CodeMirror-search-field').toggleClass('not-found', val && !_this.history.searchPrev(val));
            e.preventDefault();
            e.stopPropagation();
          }
          if (e.keyCode === 67 && e.ctrlKey) {
            close();
          }
          return false;
        };
      })(this),
      onClose: (function(_this) {
        return function(dialog) {
          _this.history.rollbackSearch();
          return _this.$code_mirror.removeClass('extra-dialog');
        };
      })(this)
    });
    return close.back = back;
  };

  Prompt.prototype.insert = function(str) {
    return this.code_mirror.replaceRange(str, this.code_mirror.getCursor());
  };

  Prompt.prototype.changes = function() {
    return window.setTimeout((function(_this) {
      return function() {
        return _this.wdb.interpreter.scroll();
      };
    })(this));
  };

  Prompt.prototype.insertHistory = function(direction) {
    var h;
    h = this.history.getHistory(direction).reverse().join('\n');
    this.history.reset();
    return this.set(h);
  };

  return Prompt;

})(Log);

Watchers = (function(superClass) {
  extend(Watchers, superClass);

  function Watchers(wdb) {
    this.wdb = wdb;
    Watchers.__super__.constructor.call(this);
    this.$watchers = $('.watchers').on('click', '.watching .name', this.unwatch.bind(this));
  }

  Watchers.prototype.unwatch = function(e) {
    var expr;
    expr = $(e.currentTarget).closest('.watching').attr('data-expr');
    return this.wdb.unwatch(expr);
  };

  Watchers.prototype.updateAll = function(watchers) {
    var value, watcher;
    for (watcher in watchers) {
      if (!hasProp.call(watchers, watcher)) continue;
      value = watchers[watcher];
      this.update(watcher, value);
    }
    this.$watchers.find('.watching:not(.updated)').remove();
    return this.$watchers.find('.watching').removeClass('updated');
  };

  Watchers.prototype.update = function(watcher, value) {
    var $name, $value, $watcher;
    $watcher = this.$watchers.find(".watching").filter(function(e) {
      return $(e).attr('data-expr') === watcher;
    });
    if (!$watcher.length) {
      $name = $('<code>', {
        "class": "name"
      });
      $value = $('<div>', {
        "class": "value"
      });
      this.$watchers.append($watcher = $('<div>', {
        "class": "watching"
      }).attr('data-expr', watcher).append($name.text(watcher), $('<code>').text(': '), $value));
      this.wdb.code($value, value.toString(), [], true);
    } else {
      $watcher.find('.value code').remove();
      this.wdb.code($watcher.find('.value'), value.toString(), [], true);
    }
    return $watcher.addClass('updated');
  };

  return Watchers;

})(Log);

Switch = (function(superClass) {
  extend(Switch, superClass);

  function Switch(wdb) {
    this.wdb = wdb;
    Switch.__super__.constructor.call(this);
    this.$trace = $('.trace');
    this.$switches = $('.switch').click((function(_this) {
      return function(e) {
        return _this["switch"]($(e.currentTarget));
      };
    })(this));
    this.$command = $('.command').click((function(_this) {
      return function(e) {
        return _this.command($(e.currentTarget));
      };
    })(this));
    this.$source = $('.source');
    this.$interpreter = $('.interpreter');
  }

  Switch.prototype["switch"] = function($switch) {
    if ($switch.is('.power')) {
      if ($switch.is('.off')) {
        return this.wdb.disable();
      } else if ($switch.is('.on')) {
        return parent.postMessage('activate', '*');
      }
    } else if ($switch.is('.code')) {
      if ($switch.is('.off')) {
        return this.open_code();
      } else if ($switch.is('.on')) {
        return this.close_code();
      }
    } else if ($switch.is('.term')) {
      if ($switch.is('.off')) {
        return this.open_term();
      } else if ($switch.is('.on')) {
        return this.close_term();
      }
    }
  };

  Switch.prototype.open_trace = function() {
    return this.$trace.addClass('mdl-layout--fixed-drawer');
  };

  Switch.prototype.close_trace = function() {
    return this.$trace.removeClass('mdl-layout--fixed-drawer');
  };

  Switch.prototype.open_code = function() {
    this.$switches.filter('.code').removeClass('off').addClass('on').removeClass('mdl-button--accent');
    this.$source.removeClass('hidden');
    return this.wdb.source.size();
  };

  Switch.prototype.close_code = function() {
    this.$switches.filter('.code').removeClass('on').addClass('off').addClass('mdl-button--accent');
    this.$source.addClass('hidden');
    return this.wdb.source.size();
  };

  Switch.prototype.open_term = function() {
    this.$switches.filter('.term').removeClass('off').addClass('on').removeClass('mdl-button--accent');
    this.$interpreter.removeClass('hidden');
    return this.wdb.source.size();
  };

  Switch.prototype.close_term = function() {
    this.$switches.filter('.term').removeClass('on').addClass('off').addClass('mdl-button--accent');
    this.$interpreter.addClass('hidden');
    return this.wdb.source.size();
  };

  Switch.prototype.command = function($command) {
    return this.wdb.execute('.' + $command.attr('data-command'));
  };

  return Switch;

})(Log);

help = "<div class=\"mdl-tabs mdl-js-tabs mdl-js-ripple-effect\">\n  <div class=\"mdl-tabs__tab-bar\">\n      <a href=\"#help-stepping\" class=\"mdl-tabs__tab is-active\">Stepping</a>\n      <a href=\"#help-breakpoints\" class=\"mdl-tabs__tab\">Breakpoints</a>\n      <a href=\"#help-inspecting\" class=\"mdl-tabs__tab\">Inspecting</a>\n      <a href=\"#help-prompt\" class=\"mdl-tabs__tab\">Prompt</a>\n      <a href=\"#help-misc\" class=\"mdl-tabs__tab\">Misc</a>\n  </div>\n\n  <div class=\"mdl-tabs__panel is-active\" id=\"help-stepping\">\n    <table class=\"mdl-data-table mdl-js-data-table mdl-shadow--2dp\">\n      <tr>\n        <td class=\"cmd\">\n          <samp>.s</samp> or <kbd>Alt</kbd> + <kbd>↓</kbd> or <kbd>F11</kbd>\n        </td>\n        <td class=\"mdl-data-table__cell--non-numeric dfn\">\n          Step into\n        </td>\n      </tr>\n      <tr>\n        <td class=\"cmd\">\n          <samp>.n</samp> or <kbd>Alt</kbd> + <kbd>→</kbd> or <kbd>F10</kbd>\n        </td>\n        <td class=\"mdl-data-table__cell--non-numeric dfn\">\n          Step over (Next)\n        </td>\n      </tr>\n      <tr>\n        <td class=\"cmd\">\n          <samp>.u</samp> or <kbd>Alt</kbd> + <kbd>←</kbd> or <kbd>F7</kbd>\n        </td>\n        <td class=\"mdl-data-table__cell--non-numeric dfn\">\n          Until (Next over loops)\n        </td>\n      </tr>\n      <tr>\n        <td class=\"cmd\">\n          <samp>.r</samp> or <kbd>Alt</kbd> + <kbd>↑</kbd> or <kbd>F9</kbd>\n        </td>\n        <td class=\"mdl-data-table__cell--non-numeric dfn\">\n          Step out (Return)\n        </td>\n      </tr>\n      <tr>\n        <td class=\"cmd\">\n          <samp>.c</samp> or <kbd>Alt</kbd> + <kbd>Enter</kbd> or <kbd>F8</kbd>\n        </td>\n        <td class=\"mdl-data-table__cell--non-numeric dfn\">\n          Continue\n        </td>\n      </tr>\n      <tr>\n        <td class=\"cmd\"><samp>.j</samp> lineno</td>\n        <td class=\"mdl-data-table__cell--non-numeric dfn\">\n          Jump to lineno (Must be at bottom frame and in the same function)\n        </td>\n      </tr>\n      <tr>\n        <td class=\"cmd\"><samp>.q</samp></td>\n        <td class=\"mdl-data-table__cell--non-numeric dfn\">\n          Quit\n        </td>\n      </tr>\n    </table>\n    <aside class=\"note\">\n      All commands are prefixed with a dot and can be\n      executed with <kbd>Alt</kbd> + <kbd>the-command-letter</kbd>,\n      i.e.: <kbd>Alt</kbd> + <kbd>h</kbd>\n    </aside>\n  </div>\n  <div class=\"mdl-tabs__panel\" id=\"help-breakpoints\">\n    <table class=\"mdl-data-table mdl-js-data-table mdl-shadow--2dp\">\n      <tr>\n        <td class=\"cmd\"><samp>.b</samp> arg</td>\n        <td class=\"mdl-data-table__cell--non-numeric dfn\">\n          Set a session breakpoint\n        </td>\n      </tr>\n      <tr>\n        <td class=\"cmd\"><samp>.t</samp> arg</td>\n        <td class=\"mdl-data-table__cell--non-numeric dfn\">\n          Set a temporary breakpoint\n        </td>\n      </tr>\n      <tr>\n        <td class=\"cmd\"><samp>.z</samp> arg</td>\n        <td class=\"mdl-data-table__cell--non-numeric dfn\">\n          Delete existing breakpoint\n        </td>\n      </tr>\n      <tr>\n        <td class=\"cmd\"><samp>.l</samp></td>\n        <td class=\"mdl-data-table__cell--non-numeric dfn\">\n          List active breakpoints\n        </td>\n      </tr>\n      <tr>\n        <td class=\"cmd\">Breakpoint argument format</td>\n        <td class=\"mdl-data-table__cell--non-numeric dfn\">\n          <code>[file/module][:lineno][#function][,condition]</code>\n        </td>\n      </tr>\n      <tr>\n        <td class=\"cmd\"><code>[file]</code></td>\n        <td class=\"mdl-data-table__cell--non-numeric dfn\">\n          Break if any line of <code>file</code> is executed</td>\n      </tr>\n      <tr>\n        <td class=\"cmd\"><code>[file]:lineno</code></td>\n        <td class=\"mdl-data-table__cell--non-numeric dfn\">\n          Break on <code>file</code> at <code>lineno</code></td>\n      </tr>\n      <tr>\n        <td class=\"cmd\"><code>[file][:lineno],condition</code></td>\n        <td class=\"mdl-data-table__cell--non-numeric dfn\">\n            Break on <code>file</code> at <code>lineno</code> if\n            <code>condition</code> is <code>True</code>\n            (ie: <code>i == 10)</code></td>\n      </tr>\n      <tr>\n        <td class=\"cmd\"><code>[file]#function</code></td>\n        <td class=\"mdl-data-table__cell--non-numeric dfn\">\n          Break when inside <code>function</code> function</td>\n      </tr>\n    </table>\n    <aside class=\"note\">\n      File is always current file by default and you can also\n      specify a module like <code>logging.config</code>.\n    </aside>\n  </div>\n  <div class=\"mdl-tabs__panel\" id=\"help-inspecting\">\n    <table class=\"mdl-data-table mdl-js-data-table mdl-shadow--2dp\">\n    <tr>\n      <td class=\"cmd\"><samp>.a</samp></td>\n      <td class=\"mdl-data-table__cell--non-numeric dfn\">\n        Echo all typed commands in the current debugging session\n      </td>\n    </tr>\n    <tr>\n      <td class=\"cmd\"><samp>.d</samp> expression</td>\n      <td class=\"mdl-data-table__cell--non-numeric dfn\">\n        Dump the result of expression in a table\n      </td>\n    </tr>\n    <tr>\n      <td class=\"cmd\"><samp>.w</samp> expression</td>\n      <td class=\"mdl-data-table__cell--non-numeric dfn\">\n        Watch expression in current file (Click on the name to remove)\n      </td>\n    </tr>\n    <tr>\n      <td class=\"cmd\"><samp>.i</samp> [mime/type;]expression</td>\n      <td class=\"mdl-data-table__cell--non-numeric dfn\">\n        Display the result in an embed, mime type defaults to \"text/html\"\n      </td>\n    </tr>\n    <tr>\n      <td class=\"cmd\"><samp>.x</samp> left ? right</td>\n      <td class=\"mdl-data-table__cell--non-numeric dfn\">\n        Display the difference between the pretty print of 'left' and 'right'\n      </td>\n    </tr>\n    <tr>\n      <td class=\"cmd\"><samp>.x</samp> left <> right</td>\n      <td class=\"mdl-data-table__cell--non-numeric dfn\">\n        Display the difference between the repr of 'left' and 'right'\n      </td>\n    </tr>\n    <tr>\n      <td class=\"cmd\"><samp>.f</samp> key in expression</td>\n      <td class=\"mdl-data-table__cell--non-numeric dfn\">\n        Search recursively the presence of key in expression object tree\n      </td>\n    </tr>\n    <tr>\n      <td class=\"cmd\"><samp>.f</samp> test of expression</td>\n      <td class=\"mdl-data-table__cell--non-numeric dfn\">\n        Search recursively values that match test in expression inner tree.\n        i.e.: .f type(x) == int of sys\n      </td>\n    </tr>\n  </table>\n</div>\n<div class=\"mdl-tabs__panel\" id=\"help-prompt\">\n  <table class=\"mdl-data-table mdl-js-data-table mdl-shadow--2dp\">\n    <tr>\n      <td class=\"cmd\">iterable!sthg</td>\n      <td class=\"mdl-data-table__cell--non-numeric dfn\">\n        If <a href=\"https://github.com/paradoxxxzero/cutter\">\n          cutter\n        </a> is installed, executes cut(iterable).sthg\n      </td>\n    </tr>\n    <tr>\n      <td class=\"cmd\">expr >! file</td>\n      <td class=\"mdl-data-table__cell--non-numeric dfn\">\n        Write the result of expr in file\n      </td>\n    </tr>\n    <tr>\n      <td class=\"cmd\">!< file</td>\n      <td class=\"mdl-data-table__cell--non-numeric dfn\">\n        Eval the content of file\n      </td>\n    </tr>\n    <tr>\n      <td class=\"cmd\"><kbd>Enter</kbd></td>\n      <td class=\"mdl-data-table__cell--non-numeric dfn\">\n        Eval the current selected text in page,\n        useful to eval code in the source\n      </td>\n    </tr>\n    <tr>\n      <td class=\"cmd\"><kbd>Shift</kbd> + <kbd>Enter</kbd></td>\n      <td class=\"mdl-data-table__cell--non-numeric dfn\">\n        Insert the current selected text in page in the prompt\n      </td>\n    </tr>\n    <tr>\n      <td class=\"cmd\"><kbd>Ctrl</kbd> + <kbd>Enter</kbd></td>\n      <td class=\"mdl-data-table__cell--non-numeric dfn\">\n        Force multiline prompt\n      </td>\n    </tr>\n  </table>\n</div>\n<div class=\"mdl-tabs__panel\" id=\"help-misc\">\n  <table class=\"mdl-data-table mdl-js-data-table mdl-shadow--2dp\">\n    <tr>\n      <td class=\"cmd\"><samp>.h</samp></td>\n      <td class=\"mdl-data-table__cell--non-numeric dfn\">\n        Get some help\n      </td>\n    </tr>\n    <tr>\n      <td class=\"cmd\"><samp>.m</samp></td>\n      <td class=\"mdl-data-table__cell--non-numeric dfn\">\n        Restart program\n      </td>\n    </tr>\n    <tr>\n      <td class=\"cmd\"><samp>.e</samp></td>\n      <td class=\"mdl-data-table__cell--non-numeric dfn\">\n        Toggle file edition mode\n      </td>\n    </tr>\n    <tr>\n      <td class=\"cmd\"><samp>.o</samp></td>\n      <td class=\"mdl-data-table__cell--non-numeric dfn\">\n        Try to open file in external ($EDITOR / $VISUAL / xdg-open) editor.\n        <br>\n        Add an argument (or hold shift with alt+o) if your editor does not\n        support the file:lno:col syntax.\n      </td>\n    </tr>\n    <tr>\n      <td class=\"cmd\"><samp>.g</samp></td>\n      <td class=\"mdl-data-table__cell--non-numeric dfn\">\n        Clear scrollback\n      </td>\n    </tr>\n  </table>\n</div>";

Wdb = (function(superClass) {
  extend(Wdb, superClass);

  Wdb.prototype.__version__ = '3.3.0';

  function Wdb() {
    Wdb.__super__.constructor.call(this);
    this.started = false;
    this.cwd = null;
    this.file_cache = {};
    this.last_cmd = null;
    this.evalTime = null;
    this.ws = new Websocket(this, $('[data-uuid]').attr('data-uuid'));
    this.traceback = new Traceback(this);
    this.source = new Source(this);
    this.interpreter = new Interpreter(this);
    this.prompt = new Prompt(this);
    this["switch"] = new Switch(this);
    this.watchers = new Watchers(this);
    this.$patience = $('.patience');
    $(window).on('beforeunload', this.unload.bind(this));
  }

  Wdb.prototype.opening = function() {
    if (!this.started) {
      $(window).on('keydown', this.global_key.bind(this));
      this.started = true;
    }
    this.ws.send('Start');
    return this["switch"].open_term();
  };

  Wdb.prototype.working = function() {
    return $('body,.activity').addClass('is-active');
  };

  Wdb.prototype.chilling = function() {
    return $('body,.activity').removeClass('is-active');
  };

  Wdb.prototype.done = function() {
    this.interpreter.scroll();
    this.prompt.ready();
    return this.chilling();
  };

  Wdb.prototype.init = function(data) {
    var base, brk, brks, j, len, name1, results;
    if (data.version !== this.constructor.prototype.__version__) {
      this.print({
        "for": 'Client Server version mismatch !',
        result: "Server is " + this.constructor.prototype.__version__ + " and Client is " + (data.version || '<= 2.0')
      });
    }
    this.cwd = data.cwd;
    brks = data.breaks;
    results = [];
    for (j = 0, len = brks.length; j < len; j++) {
      brk = brks[j];
      if ((base = this.source.breakpoints)[name1 = brk.fn] == null) {
        base[name1] = [];
      }
      results.push(this.source.breakpoints[brk.fn].push(brk));
    }
    return results;
  };

  Wdb.prototype.title = function(data) {
    $('.title').text(data.title).attr('title', data.title);
    return $('.subtitle').text(data.subtitle).attr('title', data.subtitle);
  };

  Wdb.prototype.trace = function(data) {
    this["switch"].open_trace();
    return this.traceback.make_trace(data.trace);
  };

  Wdb.prototype.select_trace = function(level) {
    return this.ws.send('Select', level);
  };

  Wdb.prototype.selectcheck = function(data) {
    if (!(data.name in this.file_cache)) {
      return this.ws.send('File', data.name);
    } else {
      data.file = this.file_cache[data.name];
      return this.select(data);
    }
  };

  Wdb.prototype.select = function(data) {
    var current_frame;
    current_frame = data.frame;
    this["switch"].open_code();
    $('.trace-line').removeClass('selected');
    $('.trace-' + current_frame.level).addClass('selected');
    this.file_cache[data.name] = data.file;
    this.source.open(data, current_frame);
    return this.done();
  };

  Wdb.prototype.ellipsize = function($code) {
    return $code.find('span.cm-string').each(function() {
      var txt;
      txt = $(this).text();
      if (txt.length > 128) {
        $(this).text('');
        $(this).append($('<span class="short close">').text(txt.substr(0, 128)));
        return $(this).append($('<span class="long">').text(txt.substr(128)));
      }
    });
  };

  Wdb.prototype.code = function(parent, src, classes, html, title, mode) {
    var $code, $node, cls, j, len;
    if (classes == null) {
      classes = [];
    }
    if (html == null) {
      html = false;
    }
    if (title == null) {
      title = null;
    }
    if (mode == null) {
      mode = "python";
    }
    if (html) {
      if (src[0] !== '<' || src.slice(-1) !== '>') {
        $node = $('<div>', {
          "class": 'out'
        }).html(src);
      } else {
        $node = $(src);
      }
      parent.append($node);
      $node.add($node.find('*')).contents().filter(function() {
        return this.nodeType === 3 && this.nodeValue.length > 0 && !$(this.parentElement).closest('thead').length;
      }).wrap('<code>').parent().each((function(_this) {
        return function(i, elt) {
          var $code, cls, j, len;
          $code = $(elt);
          $code.addClass('waiting_for_hl').addClass('cm-s-default');
          for (j = 0, len = classes.length; j < len; j++) {
            cls = classes[j];
            $code.addClass(cls);
          }
          if (title) {
            $code.attr('title', title);
          }
          return setTimeout((function() {
            CodeMirror.runMode($code.text(), mode, $code.get(0));
            $code.removeClass('waiting_for_hl');
            return _this.ellipsize($code);
          }), 50);
        };
      })(this));
    } else {
      $code = $('<code>', {
        'class': 'cm-s-default'
      });
      for (j = 0, len = classes.length; j < len; j++) {
        cls = classes[j];
        $code.addClass(cls);
      }
      if (title) {
        $code.attr('title', title);
      }
      parent.append($code);
      CodeMirror.runMode(src, mode, $code.get(0));
      this.ellipsize($code);
    }
    return $code;
  };

  Wdb.prototype.execute = function(snippet) {
    var cmd, data, key, raf, sent, space;
    cmd = (function(_this) {
      return function() {
        _this.ws.send.apply(_this.ws, arguments);
        _this.last_cmd = arguments;
        return _this.working();
      };
    })(this);
    if (snippet.indexOf('.') === 0) {
      space = snippet.indexOf(' ');
      if (space > -1) {
        key = snippet.substr(1, space - 1);
        data = snippet.substr(space + 1);
      } else {
        key = snippet.substr(1);
        data = '';
      }
      sent = (function() {
        switch (key) {
          case 'a':
            return this.printHistory();
          case 'b':
            return this.toggle_break(data);
          case 'c':
            return cmd('Continue');
          case 'd':
            if (data) {
              return cmd('Dump', data);
            }
            break;
          case 'e':
            return this.source.toggle_edition();
          case 'f':
            if (data) {
              return cmd('Find', data);
            }
            break;
          case 'g':
            return this.cls();
          case 'h':
            return this.printHelp();
          case 'i':
            if (data) {
              return cmd('Display', data);
            }
            break;
          case 'j':
            if (data) {
              return cmd('Jump', data);
            }
            break;
          case 'k':
            return this.clearHistory();
          case 'l':
            return cmd('Breakpoints');
          case 'm':
            return cmd('Restart');
          case 'n':
            return cmd('Next');
          case 'o':
            return this.source.external(!data);
          case 'q':
            return cmd('Quit');
          case 'r':
            return cmd('Return');
          case 's':
            return cmd('Step');
          case 't':
            return this.toggle_break(data, true);
          case 'u':
            return cmd('Until');
          case 'w':
            if (data) {
              return cmd('Watch', data);
            }
            break;
          case 'x':
            if (data) {
              return cmd('Diff', data);
            }
            break;
          case 'z':
            return this.toggle_break(data, false, true);
        }
      }).call(this);
      if (!sent) {
        this.prompt.unlock();
      }
      return;
    } else if (snippet.indexOf('?') === 0) {
      cmd('Dump', snippet.slice(1).trim());
      return;
    } else if (snippet === '' && this.last_cmd) {
      cmd.apply(this, this.last_cmd);
      return;
    }
    if (snippet) {
      this.working();
      this.ws.send('Eval', snippet);
      this.evalTime = typeof performance !== "undefined" && performance !== null ? performance.now() : void 0;
      this.$patience.text(this.pretty_time(0));
      raf = (function(_this) {
        return function() {
          var duration;
          if (!_this.evalTime) {
            _this.$patience.text('');
            return;
          }
          duration = parseInt((performance.now() - _this.evalTime) * 1000);
          _this.$patience.text(_this.pretty_time(duration));
          return requestAnimationFrame(raf);
        };
      })(this);
      return requestAnimationFrame(raf);
    }
  };

  Wdb.prototype.cls = function() {
    this.interpreter.clear();
    return this.done();
  };

  Wdb.prototype.printHistory = function(hist) {
    return this.print({
      "for": 'History',
      result: this.prompt.history.getSessionHistory().reverse().filter(function(e) {
        return e.indexOf('.') !== 0;
      }).join('\n')
    });
  };

  Wdb.prototype.clearHistory = function() {
    return this.prompt.history.clear();
  };

  Wdb.prototype.printHelp = function() {
    this.dialog('Help', help);
    return this.done();
  };

  Wdb.prototype.print = function(data) {
    var $group, $result, $timeholder, duration, print_duration, print_start;
    if (this.evalTime) {
      duration = parseInt((performance.now() - this.evalTime) * 1000);
      print_start = performance.now();
      this.evalTime = null;
    }
    $group = $('<div>', {
      "class": 'printed scroll-line'
    });
    this.interpreter.write($group);
    $group.append($timeholder = $('<div>'));
    this.code($group, data["for"], ['for prompted']);
    $result = $('<div>', {
      "class": 'result'
    });
    $group.append($result);
    this.code($result, data.result || ' ', ['val'], true);
    print_duration = parseInt((performance.now() - print_start) * 1000);
    if (data.duration) {
      this.code($timeholder, this.pretty_time(data.duration), ['duration'], false, "Total " + (this.pretty_time(duration)) + " + " + (this.pretty_time(print_duration)) + " of rendering");
    }
    return this.done();
  };

  Wdb.prototype.echo = function(data) {
    var $group, $result;
    $group = $('<div>', {
      "class": 'echoed scroll-line'
    });
    this.interpreter.write($group);
    this.code($group, data["for"], ['for prompted']);
    $result = $('<div>', {
      "class": 'result'
    });
    $group.append($result);
    this.code($result, data.val || '', ['val'], true, null, data.mode);
    return this.done();
  };

  Wdb.prototype.rawhtml = function(data) {
    var $group;
    $group = $('<div>', {
      "class": 'rawhtml scroll-line'
    });
    this.interpreter.write($group);
    this.code($group, data["for"], ['for prompted']);
    this.interpreter.write(data.val);
    return this.done();
  };

  Wdb.prototype.dump = function(data) {
    var $attr_head, $attr_tbody, $container, $core_head, $core_tbody, $group, $method_head, $method_tbody, $table, $tbody, key, ref, val;
    $group = $('<div>', {
      "class": 'dump scroll-line'
    });
    this.interpreter.write($group);
    this.code($group, data["for"], ['for prompted']);
    $container = $('<div>');
    $table = $('<table>', {
      "class": 'mdl-data-table mdl-js-data-table mdl-shadow--2dp object'
    }).appendTo($container);
    $core_head = $('<thead>', {
      "class": 'toggle closed'
    }).append($('<tr>').append($('<th>', {
      "class": 'core',
      colspan: 2
    }).text('Core Members'))).appendTo($table);
    $core_tbody = $('<tbody>', {
      "class": 'core closed'
    }).appendTo($table);
    $method_head = $('<thead>', {
      "class": 'toggle closed'
    }).append($('<tr>').append($('<th>', {
      "class": 'method',
      colspan: 2
    }).text('Methods'))).appendTo($table);
    $method_tbody = $('<tbody>', {
      "class": 'method closed'
    }).appendTo($table);
    $attr_head = $('<thead>', {
      "class": 'toggle closed'
    }).append($('<tr>').append($('<th>', {
      "class": 'attr',
      colspan: 2
    }).text('Attributes'))).appendTo($table);
    $attr_tbody = $('<tbody>', {
      "class": 'attr closed'
    }).appendTo($table);
    ref = data.val;
    for (key in ref) {
      val = ref[key];
      $tbody = $attr_tbody;
      if (key.indexOf('__') === 0 && key.indexOf('__', key.length - 2) !== -1) {
        $tbody = $core_tbody;
      } else if (val.type.indexOf('method') !== -1) {
        $tbody = $method_tbody;
      }
      $tbody.append($('<tr>').append($('<td>', {
        "class": 'key'
      }).text(key)).append($('<td>', {
        "class": 'mdl-data-table__cell--non-numeric val'
      }).html(val.val)));
    }
    if ($core_tbody.find('tr').length === 0) {
      $core_head.remove();
      $core_tbody.remove();
    }
    if ($attr_tbody.find('tr').length === 0) {
      $attr_head.remove();
      $attr_tbody.remove();
    }
    if ($method_tbody.find('tr').length === 0) {
      $method_head.remove();
      $method_tbody.remove();
    }
    if (data.doc) {
      $table.append($('<thead>', {
        "class": 'toggle closed'
      }).append($('<tr>').append($('<th>', {
        "class": 'doc',
        colspan: 2
      }).text('Documentation'))));
      $('<tbody>', {
        "class": 'doc closed'
      }).append($('<tr>').append($('<td>', {
        "class": 'mdl-data-table__cell--non-numeric doc',
        colspan: 2
      }).text(data.doc))).appendTo($table);
    }
    if (data.source) {
      $table.append($('<thead>', {
        "class": 'toggle closed'
      }).append($('<tr>').append($('<th>', {
        "class": 'source',
        colspan: 2
      }).text('Source'))));
      $('<tbody>', {
        "class": 'source closed'
      }).append($('<tr>').append($('<td>', {
        "class": 'mdl-data-table__cell--non-numeric source',
        colspan: 2
      }).text(data.source))).appendTo($table);
    }
    componentHandler.upgradeElement($table.get(0));
    this.code($group, $container.html(), [], true);
    return this.done();
  };

  Wdb.prototype.breakset = function(data) {
    var ref;
    this.source.set_breakpoint(data);
    if (this.prompt.get()[0] === '.' && ((ref = this.prompt.get()[1]) === 'b' || ref === 't')) {
      return this.done();
    } else {
      return this.chilling();
    }
  };

  Wdb.prototype.breakunset = function(data) {
    var ref;
    this.source.clear_breakpoint(data);
    if (this.prompt.get()[0] === '.' && ((ref = this.prompt.get()[1]) === 'b' || ref === 't' || ref === 'z')) {
      return this.done();
    } else {
      return this.chilling();
    }
  };

  Wdb.prototype.split = function(str, char) {
    var split;
    if (indexOf.call(str, char) >= 0) {
      split = str.split(char);
      return [split[0], split.slice(1).join(char).trim()];
    } else {
      return [str, null];
    }
  };

  Wdb.prototype.toggle_break = function(arg, temporary, remove_only) {
    var brk, cmd, ebrk, exist, j, len, ref, ref1, ref2, ref3, remaining;
    if (temporary == null) {
      temporary = false;
    }
    if (remove_only == null) {
      remove_only = false;
    }
    brk = {
      lno: null,
      cond: null,
      fun: null,
      fn: null,
      temporary: temporary
    };
    remaining = arg;
    ref = this.split(remaining, ','), remaining = ref[0], brk.cond = ref[1];
    ref1 = this.split(remaining, '#'), remaining = ref1[0], brk.fun = ref1[1];
    ref2 = this.split(remaining, ':'), remaining = ref2[0], brk.lno = ref2[1];
    brk.fn = remaining || this.source.state.fn;
    brk.lno = parseInt(brk.lno) || null;
    exist = false;
    ref3 = this.source.breakpoints[brk.fn] || [];
    for (j = 0, len = ref3.length; j < len; j++) {
      ebrk = ref3[j];
      if (ebrk.fn === brk.fn && ebrk.lno === brk.lno && ebrk.cond === brk.cond && ebrk.fun === brk.fun && (ebrk.temporary === brk.temporary || remove_only)) {
        exist = true;
        brk = ebrk;
        break;
      }
    }
    if (exist || remove_only) {
      this.source.clear_breakpoint(brk);
      cmd = 'Unbreak';
      if (!brk.temporary) {
        cmd = 'Broadcast|' + cmd;
      }
      this.ws.send(cmd, brk);
      this.working();
      return;
    }
    if (brk.lno) {
      this.source.ask_breakpoint(brk.lno);
    }
    cmd = 'Break';
    if (!temporary) {
      cmd = 'Broadcast|' + cmd;
    }
    this.ws.send(cmd, brk);
    return this.working();
  };

  Wdb.prototype.watched = function(data) {
    return this.watchers.updateAll(data);
  };

  Wdb.prototype.ack = function() {
    return this.done();
  };

  Wdb.prototype.display = function(data) {
    var $group, $tag;
    $group = $('<div>', {
      "class": 'display scroll-line'
    });
    this.interpreter.write($group);
    this.code($group, data["for"], ['for prompted']);
    if (data.type.indexOf('image') >= 0) {
      $tag = $("<img>");
    } else if (data.type.indexOf('audio') >= 0) {
      $tag = $("<audio>", {
        controls: 'controls',
        autoplay: 'autoplay'
      });
    } else if (data.type.indexOf('video') >= 0 || data.type.indexOf('/ogg') >= 0) {
      $tag = $("<video>", {
        controls: 'controls',
        autoplay: 'autoplay'
      });
    } else {
      $tag = $("<iframe>");
    }
    $tag.addClass('display');
    $tag.attr('src', "data:" + data.type + ";charset=UTF-8;base64," + data.val);
    $group.append($tag);
    return this.done();
  };

  Wdb.prototype.suggest = function(data) {
    if (data) {
      return this.prompt.complete(data);
    }
  };

  Wdb.prototype.die = function() {
    this.title({
      title: 'Dead',
      subtitle: 'Program has exited'
    });
    this.ws.ws.close();
    $('body').addClass('is-dead');
    if (!$('body').attr('data-debug')) {
      return setTimeout((function() {
        return window.close();
      }), 10);
    }
  };

  Wdb.prototype.global_key = function(e) {
    var char, extra, ref, ref1, ref2, sel;
    if (this.source.rw) {
      return true;
    }
    sel = this.source.focused() && this.source.code_mirror.getSelection();
    if (e.altKey && ((65 <= (ref = e.keyCode) && ref <= 90) || (37 <= (ref1 = e.keyCode) && ref1 <= 40) || e.keyCode === 13) || (118 <= (ref2 = e.keyCode) && ref2 <= 122)) {
      char = (function() {
        switch (e.keyCode) {
          case 37:
          case 118:
            return 'u';
          case 13:
          case 119:
            return 'c';
          case 38:
          case 120:
            return 'r';
          case 39:
          case 121:
            return 'n';
          case 40:
          case 122:
            return 's';
          default:
            return String.fromCharCode(e.keyCode);
        }
      })();
      char = char.toLowerCase();
      extra = '';
      if (char === 'b' || char === 't' || char === 'z') {
        extra += ' :' + this.source.state.lno;
      }
      if (char === 'i') {
        extra = ' ' + sel;
      }
      if (char === 'o' && e.shiftKey) {
        extra = ' ' + '!';
      }
      this.execute('.' + char + extra);
      return false;
    }
    if (e.keyCode === 13) {
      if (this.prompt.focused()) {
        return;
      }
      if (!sel) {
        return;
      }
      if (e.shiftKey) {
        this.prompt.insert(sel);
        this.prompt.focus();
      } else if (e.ctrlKey) {
        this.ws.send('Watch', sel);
      } else {
        this.prompt.history.historize(sel);
        this.execute(sel);
      }
      return false;
    }
  };

  Wdb.prototype.newline = function() {
    this.prompt.ready(true);
    return this.chilling();
  };

  Wdb.prototype.inspect = function(id) {
    this.ws.send('Inspect', id);
    this.working();
    return false;
  };

  Wdb.prototype.unwatch = function(expr) {
    this.ws.send('Unwatch', expr);
    return this.working();
  };

  Wdb.prototype.paste_target = function(e) {
    var target;
    target = $(e.target).text().trim();
    if (target === '') {
      return true;
    }
    if (e.shiftKey) {
      this.prompt.insert(target);
      return;
    }
    if (e.ctrlKey) {
      this.ws.send('Watch', target);
      return;
    }
    this.prompt.history.historize(target);
    this.ws.send('Dump', target);
    this.working();
    return false;
  };

  Wdb.prototype.disable = function() {
    return this.ws.send('Disable');
  };

  Wdb.prototype.shell = function() {
    this["switch"].close_trace();
    this["switch"].close_code();
    this["switch"].open_term();
    return this.done();
  };

  Wdb.prototype.dialog = function(title, content) {
    var $dialog, dialog;
    $('.modals').append($dialog = $("<dialog class=\"mdl-dialog\">\n  <h3 class=\"mdl-dialog__title\">" + title + "</h3>\n  <div class=\"mdl-dialog__content\">\n    " + content + "\n  </div>\n  <div class=\"mdl-dialog__actions\">\n    <button type=\"button\" class=\"mdl-button dialog-close\">Close</button>\n  </div>\n</dialog>"));
    $dialog.find('.dialog-close').on('click', function() {
      $dialog.get(0).close();
      return $dialog.remove();
    });
    $dialog.find('.mdl-tabs,.mdl-data-table').each(function() {
      return componentHandler.upgradeElement(this);
    });
    $dialog.on('close', (function(_this) {
      return function() {
        return _this.prompt.ready();
      };
    })(this));
    dialog = $dialog.get(0);
    if (typeof dialogPolyfill !== "undefined" && dialogPolyfill !== null) {
      dialogPolyfill.registerDialog(dialog);
    }
    return dialog.showModal();
  };

  Wdb.prototype.pretty_time = function(time) {
    var htime, mtime, stime, with_zero;
    if (time < 1000) {
      return time + "μs";
    }
    time = time / 1000;
    if (time < 10) {
      return (time.toFixed(2)) + "ms";
    }
    if (time < 100) {
      return (time.toFixed(1)) + "ms";
    }
    if (time < 1000) {
      return (time.toFixed(0)) + "ms";
    }
    time = time / 1000;
    if (time < 10) {
      return (time.toFixed(2)) + "s";
    }
    if (time < 60) {
      return (time.toFixed(1)) + "s";
    }
    with_zero = function(s) {
      s = s.toString();
      if (s.length === 1) {
        return "0" + s;
      }
      return s;
    };
    mtime = Math.floor(time / 60);
    stime = (time - 60 * mtime).toFixed(0);
    if (mtime < 60) {
      return mtime + "m" + (with_zero(stime)) + "s";
    }
    htime = Math.floor(mtime / 60);
    mtime = (mtime - 60 * htime).toFixed(0);
    return htime + "h" + (with_zero(mtime)) + "m" + (with_zero(stime)) + "s";
  };

  Wdb.prototype.unload = function() {
    return this.ws.ws.close();
  };

  return Wdb;

})(Log);

$(function() {
  return window.wdb = new Wdb();
});
