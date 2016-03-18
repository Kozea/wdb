var Codemirror, History, Log, Prompt, Traceback, Wdb, Websocket,
  extend = function(child, parent) { for (var key in parent) { if (hasProp.call(parent, key)) child[key] = parent[key]; } function ctor() { this.constructor = child; } ctor.prototype = parent.prototype; child.prototype = new ctor(); child.__super__ = parent.prototype; return child; },
  hasProp = {}.hasOwnProperty,
  indexOf = [].indexOf || function(item) { for (var i = 0, l = this.length; i < l; i++) { if (i in this && this[i] === item) return i; } return -1; };

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
    this.wdb = wdb;
    Websocket.__super__.constructor.apply(this, arguments);
    this.url = "ws://" + document.location.host + "/websocket/" + uuid;
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
    this.log(this.time(), '<-', message);
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
    this.log('->', msg);
    return this.ws.send(msg);
  };

  return Websocket;

})(Log);

Codemirror = (function(superClass) {
  extend(Codemirror, superClass);

  function Codemirror(wdb) {
    this.wdb = wdb;
    Codemirror.__super__.constructor.apply(this, arguments);
    this.$container = $('.source-editor');
    CodeMirror.commands.save = this.save.bind(this);
    CodeMirror.keyMap.wdb = {
      Esc: this.stop_edition.bind(this),
      fallthrough: ["default"]
    };
    this.code_mirror = CodeMirror((function(_this) {
      return function(elt) {
        _this.$code_mirror = $(elt);
        return _this.$container.prepend(elt);
      };
    })(this), {
      value: 'Waiting for file',
      theme: 'material',
      keyMap: 'wdb',
      readOnly: true,
      gutters: ['breaks', 'CodeMirror-linenumbers'],
      lineNumbers: true
    });
    this.code_mirror.on('gutterClick', this.gutter_click.bind(this));
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

  Codemirror.prototype.save = function() {
    var new_file;
    new_file = this.code_mirror.getValue();
    this.wdb.ws.send('Save', this.state.fn + "|" + new_file);
    return this.state.file = new_file;
  };

  Codemirror.prototype.gutter_click = function(_, n) {
    return this.wdb.toggle_break(":" + (n + 1));
  };

  Codemirror.prototype.clear_breakpoint = function(brk) {
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

  Codemirror.prototype.ask_breakpoint = function(lno) {
    return this.add_class(lno, 'ask-breakpoint');
  };

  Codemirror.prototype.set_breakpoint = function(brk) {
    var base, name1;
    if ((base = this.breakpoints)[name1 = brk.fn] == null) {
      base[name1] = [];
    }
    this.breakpoints[brk.fn].push(brk);
    return this.mark_breakpoint(brk);
  };

  Codemirror.prototype.mark_breakpoint = function(brk) {
    if (brk.lno) {
      this.remove_class(brk.lno, 'ask-breakpoint');
      this.add_class(brk.lno, 'breakpoint');
      return this.add_mark(brk.lno, 'breakpoint', 'breaks', (brk.temporary ? '○' : '●'), this.brk_to_str(brk));
    }
  };

  Codemirror.prototype.brk_to_str = function(brk) {
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

  Codemirror.prototype.get_selection = function() {
    return this.code_mirror.getSelection().trim();
  };

  Codemirror.prototype.get_breakpoint = function(n) {
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

  Codemirror.prototype.add_class = function(lno, cls) {
    return this.code_mirror.addLineClass(lno - 1, 'background', cls);
  };

  Codemirror.prototype.remove_class = function(lno, cls) {
    return this.code_mirror.removeLineClass(lno - 1, 'background', cls);
  };

  Codemirror.prototype.add_mark = function(lno, cls, id, char, title) {
    return this.code_mirror.setGutterMarker(lno - 1, id, $('<div>', {
      "class": cls,
      title: title
    }).html(char).get(0));
  };

  Codemirror.prototype.remove_mark = function(lno) {
    return this.code_mirror.setGutterMarker(lno - 1, 'breaks', null);
  };

  Codemirror.prototype.stop_edition = function() {
    if (!this.code_mirror.getOption('readOnly')) {
      return this.toggle_edition();
    }
  };

  Codemirror.prototype.toggle_edition = function() {
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

  Codemirror.prototype.open = function(data, frame) {
    var new_state;
    new_state = {
      fn: data.name,
      file: data.file,
      fun: frame["function"],
      lno: frame.lno,
      flno: frame.flno,
      llno: frame.llno
    };
    return this.set_state(new_state);
  };

  Codemirror.prototype.set_state = function(new_state) {
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
    return this.code_mirror.scrollIntoView({
      line: this.state.lno,
      ch: 1
    }, this.$code_mirror.height() / 2);
  };

  Codemirror.prototype.get_mode = function(fn) {
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

  return Codemirror;

})(Log);

History = (function(superClass) {
  extend(History, superClass);

  function History(prompt) {
    var e, error;
    this.prompt = prompt;
    History.__super__.constructor.apply(this, arguments);
    this.index = -1;
    this.current = '';
    this.currentPos = null;
    try {
      this.history = JSON.parse(localStorage['history'] || '[]');
    } catch (error) {
      e = error;
      this.fail(e);
    }
  }

  History.prototype.up = function() {
    if (this.index === -1) {
      this.current = this.prompt.get();
      this.currentPos = this.prompt.code_mirror.getCursor();
    }
    this.index = Math.min(this.history.length - 1, this.index + 1);
    return this.sync();
  };

  History.prototype.down = function() {
    this.index = Math.max(this.index - 1, -1);
    return this.sync();
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
    return this.currentPos = null;
  };

  return History;

})(Log);

Traceback = (function(superClass) {
  extend(Traceback, superClass);

  function Traceback(wdb) {
    this.wdb = wdb;
    Traceback.__super__.constructor.apply(this, arguments);
    this.$traceback = $('.traceback');
    this.$traceback.on('click', '.trace-line', this.select.bind(this));
  }

  Traceback.prototype.select = function(e) {
    var level;
    level = $(e.currentTarget).attr('data-level');
    this.wdb.select_trace(level);
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
      ref = this.wdb.cm.breakpoints[frame.file] || [];
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
      }).text(frame.file.split('/').slice(-1)[0] + ':' + frame.lno)));
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

  return Traceback;

})(Log);

Prompt = (function(superClass) {
  extend(Prompt, superClass);

  function Prompt(wdb) {
    this.wdb = wdb;
    Prompt.__super__.constructor.apply(this, arguments);
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
      autofocus: true
    });
    CodeMirror.registerHelper("hint", "jedi", (function(_this) {
      return function(cm, callback, options) {
        var cur, tok;
        cur = cm.getCursor();
        tok = cm.getTokenAt(cur);
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
          column: cur.ch
        });
        return _this.completion = {
          cur: cur,
          tok: tok,
          from: CodeMirror.Pos(cur.line, tok.start),
          to: CodeMirror.Pos(cur.line, tok.end),
          callback: callback
        };
      };
    })(this));
    this.code_mirror.addKeyMap({
      'Enter': this.newLineOrExecute.bind(this),
      'Up': this.history.up.bind(this.history),
      'Down': this.history.down.bind(this.history),
      'Ctrl-Enter': 'newlineAndIndent',
      'Ctrl-Space': function(cm, options) {
        return CodeMirror.commands.autocomplete(cm, CodeMirror.hint.jedi, {
          async: true
        });
      },
      'PageUp': 'goLineUp',
      'PageDown': 'goLineDown'
    });
    this.code_mirror.on('keyup', function(cm, e) {
      var ref;
      if (!cm.getValue()) {
        return;
      }
      if ((10 < (ref = e.keyCode) && ref < 42)) {
        return;
      }
      return CodeMirror.commands.autocomplete(cm, CodeMirror.hint.jedi, {
        async: true,
        completeSingle: false,
        extraKeys: {
          PageUp: 'goPageUp',
          PageDown: 'goPageDown',
          Home: 'goLineStartSmart',
          End: 'goLineEnd'
        }
      });
    });
  }

  Prompt.prototype.complete = function(data) {
    var completion, cur, tok;
    if (!this.completion) {
      return;
    }
    cur = this.completion.cur;
    tok = this.completion.tok;
    return this.completion.callback({
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
    });
  };

  Prompt.prototype.newLineOrExecute = function(cm) {
    var snippet;
    snippet = cm.getValue().trim();
    if (!snippet) {
      return;
    }
    cm.setOption('readOnly', true);
    this.$container.addClass('loading');
    return this.wdb.execute(snippet);
  };

  Prompt.prototype.focus = function() {
    return this.code_mirror.focus();
  };

  Prompt.prototype.ready = function(suggest, newline) {
    var snippet;
    if (suggest == null) {
      suggest = null;
    }
    if (newline == null) {
      newline = false;
    }
    if (newline) {
      this.code_mirror.execCommand('newlineAndIndent');
    } else {
      snippet = this.code_mirror.getValue().trim();
      this.history.historize(snippet);
      this.history.reset();
      this.set(suggest || '');
    }
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

  return Prompt;

})(Log);

Wdb = (function(superClass) {
  extend(Wdb, superClass);

  Wdb.prototype.__version__ = '2.9.99';

  function Wdb() {
    Wdb.__super__.constructor.apply(this, arguments);
    this.started = false;
    this.to_complete = null;
    this.cwd = null;
    this.backsearch = null;
    this.file_cache = {};
    this.last_cmd = null;
    this.eval_time = null;
    this.waited_for_ws = 0;
    this.$waiter = $('.waiter');
    this.$wdb = $('.wdb');
    this.$source = $('.source');
    this.$interpreter = $('.interpreter');
    this.$scrollback = $('.scrollback');
    this.$backsearch = $('.backsearch');
    this.$watchers = $('.watchers');
    this.ws = new Websocket(this, this.$wdb.find('[data-uuid]').attr('data-uuid'));
    this.traceback = new Traceback(this);
    this.cm = new Codemirror(this);
    this.prompt = new Prompt(this);
  }

  Wdb.prototype.opening = function() {
    if (!this.started) {
      $(window).on('keydown', this.global_key.bind(this));
      this.$scrollback.add(this.$watchers).on('click', 'a.inspect', this.inspect.bind(this)).on('click', '.short.close', this.short_open.bind(this)).on('click', '.short.open', this.short_close.bind(this)).on('click', '.toggle', this.toggle_visibility.bind(this));
      this.$watchers.on('click', '.watching .name', this.unwatch.bind(this));
      this.$source.find('.source-editor').on('mouseup', this.paste_target.bind(this));
      $('.deactivate').click(this.disable.bind(this));
      this.$interpreter.on('keydown', (function(_this) {
        return function(e) {
          var ref, ref1, ref2, scroll, way;
          if (e.ctrlKey && (37 <= (ref = e.keyCode) && ref <= 40) || (118 <= (ref1 = e.keyCode) && ref1 <= 122) || e.keyCode === 13) {
            return true;
          }
          if (e.shiftKey && ((ref2 = e.keyCode) === 33 || ref2 === 34)) {
            scroll = _this.$interpreter.height() * 2 / 3;
            way = e.keyCode === 33 ? -1 : 1;
            _this.$interpreter.stop(true, true).animate({
              scrollTop: _this.$interpreter.scrollTop() + way * scroll
            }, 250);
            return false;
          }
          return _this.prompt.focus();
        };
      })(this));
      false;
      this.started = true;
    }
    this.ws.send('Start');
    this.$waiter.remove();
    return this.$wdb.show();
  };

  Wdb.prototype.working = function() {
    return $('.activity').addClass('is-active');
  };

  Wdb.prototype.chilling = function() {
    return $('.activity').removeClass('is-active');
  };

  Wdb.prototype.done = function(suggest) {
    if (suggest == null) {
      suggest = null;
    }
    this.termscroll();
    this.prompt.ready(suggest);
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
      if ((base = this.cm.breakpoints)[name1 = brk.fn] == null) {
        base[name1] = [];
      }
      results.push(this.cm.breakpoints[brk.fn].push(brk));
    }
    return results;
  };

  Wdb.prototype.title = function(data) {
    $('.title').text(data.title).attr('title', data.title);
    return $('.subtitle').text(data.subtitle).attr('title', data.subtitle);
  };

  Wdb.prototype.trace = function(data) {
    $('.trace').addClass('mdl-layout--fixed-drawer');
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
    $('.source-editor').removeClass('hidden');
    $('.interpreter').removeClass('full-height');
    $('.trace-line').removeClass('selected');
    $('.trace-' + current_frame.level).addClass('selected');
    this.file_cache[data.name] = data.file;
    this.cm.open(data, current_frame);
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
        return this.nodeType === 3 && this.nodeValue.length > 0 && !$(this.parentElement).closest('thead').size();
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
    var cmd, data, key, space;
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
      switch (key) {
        case 'b':
          this.toggle_break(data);
          break;
        case 'c':
          cmd('Continue');
          break;
        case 'd':
          if (data) {
            cmd('Dump', data);
          }
          break;
        case 'e':
          this.cm.toggle_edition();
          break;
        case 'f':
          if (data) {
            cmd('Find', data);
          }
          break;
        case 'g':
          this.cls();
          break;
        case 'h':
          this.print_help();
          break;
        case 'i':
          if (data) {
            cmd('Display', data);
          }
          break;
        case 'j':
          if (data) {
            cmd('Jump', data);
          }
          break;
        case 'l':
          cmd('Breakpoints');
          break;
        case 'n':
          cmd('Next');
          break;
        case 'q':
          cmd('Quit');
          break;
        case 'r':
          cmd('Return');
          break;
        case 's':
          cmd('Step');
          break;
        case 't':
          this.toggle_break(data, true);
          break;
        case 'u':
          cmd('Until');
          break;
        case 'w':
          if (data) {
            cmd('Watch', data);
          }
          break;
        case 'x':
          if (data) {
            cmd('Diff', data);
          }
          break;
        case 'z':
          this.toggle_break(data, false, true);
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
      return this.eval_time = typeof performance !== "undefined" && performance !== null ? performance.now() : void 0;
    }
  };

  Wdb.prototype.cls = function() {
    this.$scrollback.empty();
    this.searchback_stop();
    return this.done();
  };

  Wdb.prototype.print_hist = function(hist) {
    return this.print({
      "for": 'History',
      result: hist.slice(0).reverse().filter(function(e) {
        return e.indexOf('.') !== 0;
      }).join('\n')
    });
  };

  Wdb.prototype.print_help = function() {
    return this.print({
      "for": 'Supported commands',
      result: '.s or [Alt] + [↓] or [F11]     : Step into\n.n or [Alt] + [→] or [F10]     : Step over (Next)\n.r or [Alt] + [↑] or [F9]      : Step out (Return)\n.c or [Alt] + [Enter] or [F8]  : Continue\n.u or [Alt] + [←] or [F7]     : Until (Next over loops)\n.j lineno                      : Jump to lineno (Must be at bottom frame and in the same function)\n.b arg                         : Set a session breakpoint  see below for what arg can be*\n.t arg                         : Set a temporary breakpoint, arg follow the same syntax as .b\n.z arg                         : Delete existing breakpoint\n.l                             : List active breakpoints\n.a                             : Echo all typed commands in the current debugging session\n.d expression                  : Dump the result of expression in a table\n.w expression                  : Watch expression in curent file (Click on the name to remove)\n.q                             : Quit\n.h                             : Get some help\n.e                             : Toggle file edition mode\n.g                             : Clear prompt\n.i [mime/type;]expression      : Display the result in an embed, mime type defaults to "text/html"\n.x left ? right                : Display the difference between the pretty print of \'left\' and \'right\'\n.x left <> right               : Display the difference between the repr of \'left\' and \'right\'\n.f key in expression           : Search recursively the presence of key in expression object tree\n.f test of expression          : Search recursively values that match test in expression inner tree.\n i.e.: .f type(x) == int of sys\n\nAll the upper commands are prefixed with a dot and can be executed with [Alt] + [the command letter], i.e.: [Alt] + [h]\n\niterable!sthg                  : If cutter is installed, executes cut(iterable).sthg\nexpr >! file                   : Write the result of expr in file\n!< file                        : Eval the content of file\n[Enter]                        : Eval the current selected text in page, useful to eval code in the source\n[Shift] + [Enter]              : Insert the current selected text in page in the prompt\n[Ctrl] + [Enter]               : Multiline prompt or execute if already in multiline mode.\n\n* arg is using the following syntax:\n    [file/module][:lineno][#function][,condition]\nwhich means:\n    - [file]                    : Break if any line of `file` is executed\n    - [file]:lineno             : Break on `file` at `lineno`\n    - [file][:lineno],condition : Break on `file` at `lineno` if `condition` is True (ie: i == 10)\n    - [file]#function           : Break when inside `function` function\nFile is always current file by default and you can also specify a module like `logging.config`.'
    });
  };

  Wdb.prototype.termscroll = function() {
    var from, to;
    from = this.$interpreter.scrollTop();
    to = Math.max(0, this.$scrollback.outerHeight() + this.$interpreter.height());
    to = Math.min(this.$scrollback.outerHeight(), to);
    if (to - from === 0) {
      return;
    }
    return this.$interpreter.stop(true).animate({
      scrollTop: to
    }, 250);
  };

  Wdb.prototype.print = function(data) {
    var $group, $result, duration;
    if (performance && this.eval_time) {
      duration = parseInt((performance.now() - this.eval_time) * 1000);
      this.eval_time = null;
    }
    $group = $('<div>', {
      "class": 'printed scroll-line'
    });
    this.$scrollback.append($group);
    if (data.duration) {
      this.code($group, this.pretty_time(data.duration), ['duration'], false, "Total " + (this.pretty_time(duration)));
    }
    this.code($group, data["for"], ['for prompted']);
    $result = $('<div>', {
      "class": 'result'
    });
    $group.append($result);
    this.code($result, data.result, ['val'], true);
    return this.done(data.suggest);
  };

  Wdb.prototype.echo = function(data) {
    var $group;
    $group = $('<div>', {
      "class": 'echoed scroll-line'
    });
    this.$scrollback.append($group);
    this.code($group, data["for"], ['for prompted']);
    this.code($group, data.val || '', ['val'], true, null, data.mode);
    return this.done();
  };

  Wdb.prototype.rawhtml = function(data) {
    var $group;
    $group = $('<div>', {
      "class": 'rawhtml scroll-line'
    });
    this.$scrollback.append($group);
    this.code($group, data["for"], ['for prompted']);
    this.$scrollback.append(data.val);
    return this.done();
  };

  Wdb.prototype.dump = function(data) {
    var $attr_head, $attr_tbody, $container, $core_head, $core_tbody, $group, $method_head, $method_tbody, $table, $tbody, key, ref, val;
    $group = $('<div>', {
      "class": 'dump scroll-line'
    });
    this.$scrollback.append($group);
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
        "class": 'mdl-data-table__cell--non-numeric'
      }).text(key)).append($('<td>').html(val.val)));
    }
    if ($core_tbody.find('tr').size() === 0) {
      $core_head.remove();
      $core_tbody.remove();
    }
    if ($attr_tbody.find('tr').size() === 0) {
      $attr_head.remove();
      $attr_tbody.remove();
    }
    if ($method_tbody.find('tr').size() === 0) {
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
        "class": 'doc',
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
        "class": 'source',
        colspan: 2
      }).text(data.source))).appendTo($table);
    }
    componentHandler.upgradeElement($table.get(0));
    this.code($group, $container.html(), [], true);
    return this.done();
  };

  Wdb.prototype.breakset = function(data) {
    var ref;
    this.cm.set_breakpoint(data);
    if (this.$eval.val()[0] === '.' && ((ref = this.$eval.val()[1]) === 'b' || ref === 't')) {
      return this.done();
    } else {
      return this.chilling();
    }
  };

  Wdb.prototype.breakunset = function(data) {
    var ref;
    this.cm.clear_breakpoint(data);
    if (this.$eval.val()[0] === '.' && ((ref = this.$eval.val()[1]) === 'b' || ref === 't' || ref === 'z')) {
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
    brk.fn = remaining || this.cm.state.fn;
    brk.lno = parseInt(brk.lno) || null;
    exist = false;
    ref3 = this.cm.breakpoints[brk.fn] || [];
    for (j = 0, len = ref3.length; j < len; j++) {
      ebrk = ref3[j];
      if (ebrk.fn === brk.fn && ebrk.lno === brk.lno && ebrk.cond === brk.cond && ebrk.fun === brk.fun && (ebrk.temporary === brk.temporary || remove_only)) {
        exist = true;
        brk = ebrk;
        break;
      }
    }
    if (exist || remove_only) {
      this.cm.clear_breakpoint(brk);
      cmd = 'Unbreak';
      if (!brk.temporary) {
        cmd = 'Broadcast|' + cmd;
      }
      this.ws.send(cmd, brk);
      this.working();
      return;
    }
    if (brk.lno) {
      this.cm.ask_breakpoint(brk.lno);
    }
    cmd = 'Break';
    if (!temporary) {
      cmd = 'Broadcast|' + cmd;
    }
    this.ws.send(cmd, brk);
    return this.working();
  };

  Wdb.prototype.format_fun = function(p) {
    var cls, i, j, len, param, ref, tags;
    tags = [
      $('<span>', {
        "class": 'fun_name',
        title: p.module
      }).text(p.call_name), $('<span>', {
        "class": 'fun_punct'
      }).text('(')
    ];
    ref = p.params;
    for (i = j = 0, len = ref.length; j < len; i = ++j) {
      param = ref[i];
      cls = 'fun_param';
      if (i === p.index || (i === p.params.length - 1 && p.index > i)) {
        cls = 'fun_param active';
      }
      tags.push($('<span>', {
        "class": cls
      }).text(param));
      if (i !== p.params.length - 1) {
        tags.push($('<span>', {
          "class": 'fun_punct'
        }).text(', '));
      }
    }
    tags.push($('<span>', {
      "class": 'fun_punct'
    }).text(')'));
    return tags;
  };

  Wdb.prototype.watched = function(data) {
    var $name, $value, $watcher, value, watcher;
    for (watcher in data) {
      if (!hasProp.call(data, watcher)) continue;
      value = data[watcher];
      $watcher = this.$watchers.find(".watching").filter(function(e) {
        return $(e).attr('data-expr') === watcher;
      });
      if (!$watcher.size()) {
        $name = $('<code>', {
          "class": "name"
        });
        $value = $('<div>', {
          "class": "value"
        });
        this.$watchers.append($watcher = $('<div>', {
          "class": "watching"
        }).attr('data-expr', watcher).append($name.text(watcher), $('<code>').text(': '), $value));
        this.code($value, value.toString(), [], true);
      } else {
        $watcher.find('.value code').remove();
        this.code($watcher.find('.value'), value.toString(), [], true);
      }
      $watcher.addClass('updated');
    }
    this.$watchers.find('.watching:not(.updated)').remove();
    return this.$watchers.find('.watching').removeClass('updated');
  };

  Wdb.prototype.ack = function() {
    return this.$eval.val('').trigger('autosize.resize');
  };

  Wdb.prototype.display = function(data) {
    var $group, $tag;
    $group = $('<div>', {
      "class": 'display scroll-line'
    });
    this.$scrollback.append($group);
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
    return setTimeout((function() {
      return window.close();
    }), 10);
  };

  Wdb.prototype.global_key = function(e) {
    var char, extra, ref, ref1, ref2, sel;
    if (this.cm.rw) {
      return true;
    }
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
        extra += ' :' + this.cm.state.lno;
      }
      if (char === 'i') {
        extra = getSelection().toString();
      }
      this.execute('.' + char + extra);
      return false;
    }
    if (e.keyCode === 13) {
      sel = getSelection().toString();
      if (!sel) {
        return;
      }
      if (e.shiftKey) {
        this.eval_insert(sel);
      } else {
        this.prompt.history.historize(sel);
        this.execute(sel);
      }
      return false;
    }
  };

  Wdb.prototype.newline = function() {
    this.prompt.ready('', true);
    return this.chilling();
  };

  Wdb.prototype.inspect = function(e) {
    this.ws.send('Inspect', $(e.currentTarget).attr('href'));
    this.working();
    return false;
  };

  Wdb.prototype.short_open = function(e) {
    return $(e.currentTarget).addClass('open').removeClass('close').next('.long').show('fast');
  };

  Wdb.prototype.short_close = function(e) {
    return $(e.currentTarget).addClass('close').removeClass('open').next('.long').hide('fast');
  };

  Wdb.prototype.toggle_visibility = function(e) {
    return $(e.currentTarget).add($(e.currentTarget).next()).toggleClass('closed', 'shown');
  };

  Wdb.prototype.unwatch = function(e) {
    this.ws.send('Unwatch', $(e.currentTarget).closest('.watching').attr('data-expr'));
    return this.working();
  };

  Wdb.prototype.paste_target = function(e) {
    var target;
    if (e.which !== 2) {
      return;
    }
    target = $(e.target).text().trim();
    this.prompt.history.historize(target);
    this.ws.send('Dump', target);
    this.working();
    return false;
  };

  Wdb.prototype.disable = function() {
    return this.ws.send('Disable');
  };

  Wdb.prototype.shell = function() {
    $('.trace').removeClass('mdl-layout--fixed-drawer');
    $('.source-editor').addClass('hidden');
    $('.interpreter').addClass('full-height');
    return this.done();
  };

  Wdb.prototype.pretty_time = function(time) {
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
    if (time < 100) {
      return (time.toFixed(1)) + "s";
    }
    return (time.toFixed(0)) + "s";
  };

  return Wdb;

})(Log);

$((function(_this) {
  return function() {
    return _this.wdb = new Wdb();
  };
})(this));
