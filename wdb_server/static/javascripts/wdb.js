(function() {
  var Codemirror, Log, WS, Wdb, debug,
    __hasProp = {}.hasOwnProperty,
    __extends = function(child, parent) { for (var key in parent) { if (__hasProp.call(parent, key)) child[key] = parent[key]; } function ctor() { this.constructor = child; } ctor.prototype = parent.prototype; child.prototype = new ctor(); child.__super__ = parent.prototype; return child; },
    __indexOf = [].indexOf || function(item) { for (var i = 0, l = this.length; i < l; i++) { if (i in this && this[i] === item) return i; } return -1; };

  debug = true;

  Log = (function() {
    function Log() {}

    Log.prototype.log = function() {
      var log_args, name;
      if (debug) {
        name = "[" + this.constructor.name + "]";
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

  WS = (function(_super) {
    __extends(WS, _super);

    function WS(wdb) {
      this.wdb = wdb;
      this.url = "ws://" + document.location.host + "/websocket/" + _uuid;
      this.log('Opening new socket', this.url);
      this.ws = new WebSocket(this.url);
      this.ws.onclose = this.close.bind(this);
      this.ws.onopen = this.open.bind(this);
      this.ws.onerror = this.error.bind(this);
      this.ws.onmessage = this.message.bind(this);
    }

    WS.prototype.time = function() {
      var date;
      date = new Date();
      return ("" + (date.getHours()) + ":" + (date.getMinutes()) + ":") + ("" + (date.getSeconds()) + "." + (date.getMilliseconds()));
    };

    WS.prototype.close = function(m) {
      return this.log("Closed", m);
    };

    WS.prototype.error = function(m) {
      return this.fail("Error", m);
    };

    WS.prototype.open = function(m) {
      this.log("Open", m);
      return this.wdb.opening();
    };

    WS.prototype.message = function(m) {
      var cmd, data, message, pipe;
      message = m.data;
      pipe = message.indexOf('|');
      if (pipe > -1) {
        cmd = message.substr(0, pipe);
        data = JSON.parse(message.substr(pipe + 1));
      } else {
        cmd = message;
      }
      this.log(this.time(), '<-', cmd);
      cmd = cmd.toLowerCase();
      if (cmd in this.wdb) {
        return this.wdb[cmd.toLowerCase()](data);
      } else {
        return this.fail('Unknown command', cmd);
      }
    };

    WS.prototype.send = function(cmd, data) {
      var msg;
      if (data == null) {
        data = null;
      }
      if (data) {
        msg = "" + cmd + "|" + data;
      } else {
        msg = cmd;
      }
      this.log(this.time(), '->', msg);
      return this.ws.send(msg);
    };

    return WS;

  })(Log);

  Codemirror = (function(_super) {
    __extends(Codemirror, _super);

    function Codemirror(wdb) {
      this.wdb = wdb;
      CodeMirror.keyMap.wdb = {
        Esc: (function(_this) {
          return function(cm) {
            return _this.toggle_edition(false);
          };
        })(this),
        fallthrough: ["default"]
      };
      CodeMirror.commands.save = (function(_this) {
        return function() {
          return _this.wdb.ws.send('Save', "" + _this.cm._fn + "|" + (_this.cm.getValue()));
        };
      })(this);
      this.cm = null;
    }

    Codemirror.prototype["new"] = function(file, name, rw) {
      if (rw == null) {
        rw = false;
      }
      this.cm = CodeMirror((function(elt) {
        $('#source-editor').prepend(elt);
        return $(elt).addClass(rw ? 'rw' : 'ro').addClass('cm');
      }), {
        value: file,
        mode: this.get_mode(name),
        readOnly: !rw,
        theme: 'wdb',
        keyMap: 'wdb',
        gutters: ["breakpoints", "CodeMirror-linenumbers"],
        lineNumbers: true
      });
      this.cm._bg_marks = {
        cls: {},
        marks: {}
      };
      this.cm._rw = rw;
      this.cm._fn = name;
      this.cm._file = file;
      this.cm._fun = null;
      this.cm._last_hl = null;
      this.cm.on("gutterClick", (function(_this) {
        return function(cm, n) {
          _this.cm = cm;
          return _this.wdb.toggle_break(':' + (n + 1));
        };
      })(this));
      this.cm.addClass = (function(_this) {
        return function(lno, cls) {
          _this.cm.addLineClass(lno - 1, 'background', cls);
          if (_this.cm._bg_marks.cls[lno]) {
            return _this.cm._bg_marks.cls[lno] = _this.cm._bg_marks.cls[lno] + ' ' + cls;
          } else {
            return _this.cm._bg_marks.cls[lno] = cls;
          }
        };
      })(this);
      this.cm.removeClass = (function(_this) {
        return function(lno, cls) {
          _this.cm.removeLineClass(lno - 1, 'background', cls);
          return delete _this.cm._bg_marks.cls[lno];
        };
      })(this);
      this.cm.addMark = (function(_this) {
        return function(lno, cls, char) {
          _this.cm._bg_marks.marks[lno] = [cls, char];
          return _this.cm.setGutterMarker(lno - 1, "breakpoints", $('<div>', {
            "class": cls
          }).html(char).get(0));
        };
      })(this);
      return this.cm.removeMark = (function(_this) {
        return function(lno) {
          delete _this.cm._bg_marks.marks[lno];
          return _this.cm.setGutterMarker(lno - 1, "breakpoints", null);
        };
      })(this);
    };

    Codemirror.prototype.toggle_edition = function(rw) {
      var char, cls, lno, marks, scroll, _ref;
      cls = $.extend({}, this.cm._bg_marks.cls);
      marks = $.extend({}, this.cm._bg_marks.marks);
      scroll = $('#source .CodeMirror-scroll').scrollTop();
      $('#source .CodeMirror').remove();
      this.cm = this["new"](this.cm._file, this.cm._fn, rw);
      for (lno in cls) {
        this.cm.addClass(lno, cls[lno]);
      }
      for (lno in marks) {
        _ref = marks[lno], cls = _ref[0], char = _ref[1];
        this.cm.addMark(lno, cls, char);
      }
      $('#source .CodeMirror-scroll').scrollTop(scroll);
      return this.print({
        "for": "Toggling edition",
        result: "Edit mode " + (rw ? 'on' : 'off')
      });
    };

    Codemirror.prototype.select = function(data, frame) {
      var $hline, $scroll, lno, _i, _j, _len, _ref, _ref1, _ref2;
      if (!this.cm) {
        this["new"](data.file, data.name);
        this.wdb.$eval.focus();
      } else {
        if (this.cm._fn === data.name) {
          if (this.cm._fun !== frame["function"]) {
            for (lno in this.cm._bg_marks.cls) {
              this.cm.removeLineClass(lno - 1, 'background');
            }
          }
          for (lno in this.cm._bg_marks.marks) {
            this.cm.setGutterMarker(lno - 1, 'breakpoints', null);
          }
          if (this.cm._last_hl) {
            this.cm.removeLineClass(lno - 1, 'background');
            this.cm.addLineClass(lno - 1, 'background', 'footstep');
          }
        } else {
          this.cm.setValue(data.file);
          this.cm._fn = data.name;
          this.cm._fun = frame["function"];
          this.cm._file = data.file;
          this.cm._last_hl = null;
        }
        this.cm._bg_marks.cls = {};
        this.cm._bg_marks.marks = {};
      }
      _ref = data.breaks;
      for (_i = 0, _len = _ref.length; _i < _len; _i++) {
        lno = _ref[_i];
        this.cm.addClass(lno, 'breakpoint');
        this.cm.addMark(lno, 'breakpoint', '●');
      }
      this.cm.addClass(frame.lno, 'highlighted');
      this.cm.addMark(frame.lno, 'highlighted', '➤');
      if (this.cm._fun !== frame["function"] && frame["function"] !== '<module>') {
        for (lno = _j = _ref1 = frame.flno, _ref2 = frame.llno + 1; _ref1 <= _ref2 ? _j < _ref2 : _j > _ref2; lno = _ref1 <= _ref2 ? ++_j : --_j) {
          this.cm.addClass(lno, 'ctx');
          if (lno === frame.flno) {
            this.cm.addClass(lno, 'ctx-top');
          } else if (lno === frame.llno) {
            this.cm.addClass(lno, 'ctx-bottom');
          }
        }
        this.cm._fun = frame["function"];
      }
      this.cm._last_hl = frame.lno;
      this.cm.scrollIntoView({
        line: frame.lno,
        ch: 1
      }, 1);
      $scroll = $('#source .CodeMirror-scroll');
      $hline = $('#source .highlighted');
      return $scroll.scrollTop($hline.offset().top - $scroll.offset().top + $scroll.scrollTop() - $scroll.height() / 2);
    };

    Codemirror.prototype.get_mode = function(fn) {
      var ext;
      ext = fn.split('.').splice(-1)[0];
      if (ext === 'py') {
        'python';
      } else if (ext === 'jinja2') {
        'jinja2';
      }
      return 'python';
    };

    return Codemirror;

  })(Log);

  Wdb = (function(_super) {
    __extends(Wdb, _super);

    function Wdb() {
      var e;
      this.started = false;
      this.to_complete = null;
      this.ws = new WS(this);
      this.cm = new Codemirror(this);
      this.cwd = null;
      this.backsearch = null;
      this.cmd_hist = [];
      this.session_cmd_hist = {};
      this.file_cache = {};
      this.last_cmd = null;
      this.waited_for_ws = 0;
      this.$state = $('.state');
      this.$waiter = $('#waiter');
      this.$wdb = $('#wdb');
      this.$eval = $('#eval');
      this.$source = $('#source');
      this.$traceback = $('#traceback');
      this.$traceback.on('click', '.traceline', this.select_click.bind(this));
      this.$title = $('#title');
      try {
        this.cmd_hist = JSON.parse(localStorage['cmd_hist']);
      } catch (_error) {
        e = _error;
        this.fail(e);
      }
    }

    Wdb.prototype.opening = function() {
      if (!this.started) {
        this.register_handlers();
        this.started = true;
      }
      this.start();
      this.$waiter.remove();
      this.$wdb.show();
      return this.$eval.autosize();
    };

    Wdb.prototype.working = function() {
      return this.$state.addClass('on');
    };

    Wdb.prototype.chilling = function() {
      return this.$state.removeClass('on');
    };

    Wdb.prototype.start = function() {
      return this.ws.send('Start');
    };

    Wdb.prototype.init = function(data) {
      return this.cwd = data.cwd;
    };

    Wdb.prototype.title = function(data) {
      return this.$title.text(data.title).attr('title', data.title).append($('<small>').text(data.subtitle).attr('title', data.subtitle));
    };

    Wdb.prototype.trace = function(data) {
      var $tracecode, $tracefile, $tracefilelno, $tracefun, $tracefunfun, $traceline, $tracelno, frame, suffix, _i, _len, _ref, _results;
      this.$traceback.empty();
      _ref = data.trace;
      _results = [];
      for (_i = 0, _len = _ref.length; _i < _len; _i++) {
        frame = _ref[_i];
        $traceline = $('<div>').addClass('traceline').attr('id', 'trace-' + frame.level).attr('data-level', frame.level);
        if (frame.current) {
          $traceline.addClass('real-selected');
        }
        $tracefile = $('<span>').addClass('tracefile').text(frame.file);
        $tracelno = $('<span>').addClass('tracelno').text(frame.lno);
        $tracefun = $('<span>').addClass('tracefun').text(frame["function"]);
        $tracefilelno = $('<div>').addClass('tracefilelno').append($tracefile).append($tracelno);
        $tracefunfun = $('<div>').addClass('tracefunfun').append($tracefun);
        if (frame.file.indexOf('site-packages') > 0) {
          suffix = frame.file.split('site-packages').slice(-1)[0];
          $tracefile.text(suffix);
          $tracefile.prepend($('<span>').addClass('tracestar').text('*').attr({
            title: frame.file
          }));
        }
        if (frame.file.indexOf(this.cwd) === 0) {
          suffix = frame.file.split(this.cwd).slice(-1)[0];
          $tracefile.text(suffix);
          $tracefile.prepend($('<span>').addClass('tracestar').text('.').attr({
            title: frame.file
          }));
        }
        $tracecode = $('<div>').addClass('tracecode');
        this.code($tracecode, frame.code);
        $traceline.append($tracefilelno);
        $traceline.append($tracecode);
        $traceline.append($tracefunfun);
        _results.push(this.$traceback.prepend($traceline));
      }
      return _results;
    };

    Wdb.prototype.select_click = function(e) {
      return this.ws.send('Select', $(e.currentTarget).attr('data-level'));
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
      this.$source = $('#source');
      current_frame = data.frame;
      $('#interpreter').show();
      $('.traceline').removeClass('selected');
      $('#trace-' + current_frame.level).addClass('selected');
      this.$eval.val('').attr('data-index', -1).trigger('autosize.resize');
      this.file_cache[data.name] = data.file;
      this.cm.select(data, current_frame);
      return this.chilling();
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

    Wdb.prototype.code = function(parent, src, classes, html) {
      var $code, $node, cls, _i, _len;
      if (classes == null) {
        classes = [];
      }
      if (html == null) {
        html = false;
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
            var $code, cls, _i, _len;
            $code = $(elt);
            $code.addClass('waiting_for_hl').addClass('cm');
            for (_i = 0, _len = classes.length; _i < _len; _i++) {
              cls = classes[_i];
              $code.addClass(cls);
            }
            return setTimeout((function() {
              CodeMirror.runMode($code.text(), "python", $code.get(0));
              $code.removeClass('waiting_for_hl');
              return _this.ellipsize($code);
            }), 50);
          };
        })(this));
      } else {
        $code = $('<code>', {
          'class': 'cm'
        });
        for (_i = 0, _len = classes.length; _i < _len; _i++) {
          cls = classes[_i];
          $code.addClass(cls);
        }
        parent.append($code);
        CodeMirror.runMode(src, "python", $code.get(0));
        this.ellipsize($code);
      }
      return $code;
    };

    Wdb.prototype.historize = function(snippet) {
      var filename, index;
      filename = $('.selected .tracefile').text();
      if (!(filename in this.session_cmd_hist)) {
        this.session_cmd_hist[filename] = [];
      }
      while ((index = this.cmd_hist.indexOf(snippet)) !== -1) {
        this.cmd_hist.splice(index, 1);
      }
      this.cmd_hist.unshift(snippet);
      this.session_cmd_hist[filename].unshift(snippet);
      return localStorage && (localStorage['cmd_hist'] = JSON.stringify(this.cmd_hist));
    };

    Wdb.prototype.execute = function(snippet) {
      var cmd, data, key, space;
      snippet = snippet.trim();
      this.historize(snippet);
      cmd = (function(_this) {
        return function() {
          var last_cmd;
          _this.ws.send.apply(_this.ws, arguments);
          return last_cmd = arguments;
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
            cmd('Dump', data);
            break;
          case 'e':
            this.cm.toggle_edition(!this.cm.cm._rw);
            break;
          case 'g':
            this.cls();
            break;
          case 'h':
            this.print_help();
            break;
          case 'j':
            cmd('Jump', data);
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
          case 'i':
            cmd('Display', data);
            break;
          case 't':
            this.toggle_break(data, true);
            break;
          case 'u':
            cmd('Until');
            break;
          case 'w':
            cmd('Watch', data);
            break;
          case 'z':
            cmd('Unbreak', data);
            break;
          case 'f':
            this.print_hist(this.session_cmd_hist[$('.selected .tracefile').text()]);
        }
        return;
      } else if (snippet.indexOf('?') === 0) {
        cmd('Dump', snippet.slice(1).trim());
        this.working();
        this.suggest_stop();
        return;
      } else if (snippet === '' && last_cmd) {
        cmd.apply(this, last_cmd);
        return;
      }
      if (snippet) {
        this.ws.send('Eval', snippet);
        this.$eval.val(this.$eval.val() + '…').trigger('autosize.resize').prop('disabled', true);
        return this.working();
      }
    };

    Wdb.prototype.cls = function() {
      $('#completions').height($('#interpreter').height() - $('#prompt').innerHeight());
      this.termscroll();
      return this.$eval.val('').trigger('autosize.resize');
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
        result: '.s or [Ctrl] + [↓] or [F11]    : Step into\n.n or [Ctrl] + [→] or [F10]    : Step over (Next)\n.r or [Ctrl] + [↑] or [F9]     : Step out (Return)\n.c or [Ctrl] + [←] or [F8]     : Continue\n.u or [F7]                     : Until (Next over loops)\n.j lineno                      : Jump to lineno (Must be at bottom frame and in the same function)\n.b arg                         : Set a session breakpoint  see below for what arg can be*\n.t arg                         : Set a temporary breakpoint, arg follow the same syntax as .b\n.z arg                         : Delete existing breakpoint\n.l                             : List active breakpoints\n.f                             : Echo all typed commands in the current debugging session\n.d expression                  : Dump the result of expression in a table\n.w expression                  : Watch expression in curent file (Click on the name to remove)\n.q                             : Quit\n.h                             : Get some help\n.e                             : Toggle file edition mode\n.g                             : Clear prompt\n.i [mime/type;]expression      : Display the result in an embed, mime type defaults to "text/html"\niterable!sthg                  : If cutter is installed, executes cut(iterable).sthg\nexpr >! file                   : Write the result of expr in file\n!< file                        : Eval the content of file\n[Enter]                        : Eval the current selected text in page, useful to eval code in the source\n\n* arg is using the following syntax:\n    [file/module][:lineno][#function][,condition]\nwhich means:\n    - [file]                    : Break if any line of `file` is executed\n    - [file]:lineno             : Break on `file` at `lineno`\n    - [file][:lineno],condition : Break on `file` at `lineno` if `condition` is True (ie: i == 10)\n    - [file]#function           : Break when inside `function` function\nFile is always current file by default and you can also specify a module like `logging.config`.'
      });
    };

    Wdb.prototype.termscroll = function() {
      return $('#interpreter').stop(true).animate({
        scrollTop: $('#scrollback').height()
      }, 1000);
    };

    Wdb.prototype.print = function(data) {
      var snippet;
      this.suggest_stop();
      snippet = this.$eval.val();
      this.code($('#scrollback'), data["for"], ['prompted']);
      this.code($('#scrollback'), data.result, [], true);
      this.$eval.val('').prop('disabled', false).attr('data-index', -1).trigger('autosize.resize').focus();
      $('#completions').attr('style', '');
      this.termscroll();
      return this.chilling();
    };

    Wdb.prototype.echo = function(data) {
      this.code($('#scrollback'), data["for"], ['prompted']);
      this.code($('#scrollback'), data.val || '', [], true);
      this.termscroll();
      return this.chilling();
    };

    Wdb.prototype.dump = function(data) {
      var $attr_tbody, $container, $core_tbody, $method_tbody, $table, $tbody, key, val, _ref;
      this.code($('#scrollback'), data["for"], ['prompted']);
      $container = $('<div>');
      $table = $('<table>', {
        "class": 'object'
      }).appendTo($container);
      $table.append($('<thead>', {
        "class": 'toggle hidden'
      }).append($('<tr>').append($('<td>', {
        "class": 'core',
        colspan: 2
      }).text('Core Members'))));
      $core_tbody = $('<tbody>', {
        "class": 'core hidden'
      }).appendTo($table);
      $table.append($('<thead>', {
        "class": 'toggle hidden'
      }).append($('<tr>').append($('<td>', {
        "class": 'method',
        colspan: 2
      }).text('Methods'))));
      $method_tbody = $('<tbody>', {
        "class": 'method hidden'
      }).appendTo($table);
      $table.append($('<thead>', {
        "class": 'toggle shown'
      }).append($('<tr>').append($('<td>', {
        "class": 'attr',
        colspan: 2
      }).text('Attributes'))));
      $attr_tbody = $('<tbody>', {
        "class": 'attr shown'
      }).appendTo($table);
      _ref = data.val;
      for (key in _ref) {
        val = _ref[key];
        $tbody = $attr_tbody;
        if (key.indexOf('__') === 0 && key.indexOf('__', key.length - 2) !== -1) {
          $tbody = $core_tbody;
        } else if (val.type.indexOf('method') !== -1) {
          $tbody = $method_tbody;
        }
        $tbody.append($('<tr>').append($('<td>').text(key)).append($('<td>').html(val.val)));
      }
      this.code($('#scrollback'), $container.html(), [], true);
      this.termscroll();
      this.$eval.val('').prop('disabled', false).trigger('autosize.resize').focus();
      return this.chilling();
    };

    Wdb.prototype.breakset = function(data) {
      if (data.lno) {
        this.cm.cm.removeClass(data.lno, 'ask-breakpoint');
        this.cm.cm.addClass(data.lno, 'breakpoint');
        this.cm.cm.addMark(data.lno, 'breakpoint', data.temporary ? '○' : '●');
        if (data.cond) {
          $line.attr('title', "On [" + data.cond + "]");
        }
      }
      if (this.$eval.val().indexOf('.b ') === 0 || this.$eval.val().indexOf('.t ') === 0) {
        this.$eval.val('').prop('disabled', false).trigger('autosize.resize').focus();
      }
      return this.chilling();
    };

    Wdb.prototype.breakunset = function(data) {
      this.cm.cm.removeClass(data.lno, 'ask-breakpoint');
      if (this.$eval.val().indexOf('.b ') === 0) {
        this.$eval.val('').prop('disabled', false).trigger('autosize.resize').focus();
      }
      return this.chilling();
    };

    Wdb.prototype.toggle_break = function(arg, temporary) {
      var cls, cmd, lno;
      cmd = temporary ? 'TBreak' : 'Break';
      lno = NaN;
      if (arg.indexOf(':') > -1) {
        lno = arg.split(':')[1];
        if (lno.indexOf(',') > -1) {
          lno = arg.split(',')[0];
        }
        if (lno.indexOf('#') > -1) {
          lno = arg.split('#')[0];
        }
        lno = parseInt(lno);
      }
      if (isNaN(lno)) {
        this.ws.send(cmd, arg);
        return;
      }
      cls = this.cm.cm.lineInfo(lno - 1).bgClass || '';
      if (cls.split(' ').indexOf('breakpoint') > -1) {
        this.cm.cm.removeMark(lno);
        this.cm.cm.removeClass(lno, 'breakpoint');
        this.cm.cm.addClass(lno, 'ask-breakpoint');
        return this.ws.send('Unbreak', ":" + lno);
      } else {
        this.cm.cm.addClass(lno, 'ask-breakpoint');
        return this.ws.send(cmd, arg);
      }
    };

    Wdb.prototype.format_fun = function(p) {
      var cls, i, param, tags, _i, _len, _ref;
      tags = [
        $('<span>', {
          "class": 'fun_name',
          title: p.module
        }).text(p.call_name), $('<span>', {
          "class": 'fun_punct'
        }).text('(')
      ];
      _ref = p.params;
      for (i = _i = 0, _len = _ref.length; _i < _len; i = ++_i) {
        param = _ref[i];
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

    Wdb.prototype.suggest = function(data) {
      var $appender, $comp, $comp_wrapper, $tbody, $td, added, base_len, completion, height, index, param, _i, _j, _len, _len1, _ref, _ref1, _ref2;
      if (data) {
        $comp_wrapper = $('#completions');
        $comp = $('#completions table').empty();
        $comp.append($('<thead><tr><th id="comp-desc" colspan="5">'));
        height = $comp_wrapper.height();
        added = [];
        _ref = data.params;
        for (_i = 0, _len = _ref.length; _i < _len; _i++) {
          param = _ref[_i];
          $('#comp-desc').append(format_fun(param));
        }
        if (data.completions.length) {
          $tbody = $('<tbody>');
          base_len = data.completions[0].base.length;
          this.$eval.data({
            root: this.$eval.val().substr(0, this.$eval.val().length - base_len)
          });
        }
        _ref1 = data.completions;
        for (index = _j = 0, _len1 = _ref1.length; _j < _len1; index = ++_j) {
          completion = _ref1[index];
          if (_ref2 = completion.base + completion.complete, __indexOf.call(added, _ref2) >= 0) {
            continue;
          }
          added.push(completion.base + completion.complete);
          if (index % 5 === 0) {
            $tbody.append($appender = $('<tr>'));
          }
          $appender.append($td = $('<td>').attr('title', completion.description).append($('<span>').addClass('base').text(completion.base)).append($('<span>').addClass('completion').text(completion.complete)));
          if (!completion.complete) {
            $td.addClass('active complete');
            $('#comp-desc').html($td.attr('title'));
          }
        }
        $comp.append($tbody);
        $comp_wrapper.height(Math.max(height, $comp.height()));
        this.termscroll();
      }
      if (this.to_complete) {
        this.ws.send('Complete', this.to_complete);
        return this.to_complete = false;
      } else {
        return this.to_complete = null;
      }
    };

    Wdb.prototype.suggest_stop = function() {
      return $('#completions table').empty();
    };

    Wdb.prototype.watched = function(data) {
      var $name, $value, $watcher, $watchers, value, watcher;
      $watchers = $('#watchers');
      for (watcher in data) {
        if (!__hasProp.call(data, watcher)) continue;
        value = data[watcher];
        $watcher = $watchers.find(".watching").filter(function(e) {
          return $(e).attr('data-expr') === watcher;
        });
        if (!$watcher.size()) {
          $name = $('<code>', {
            "class": "name"
          });
          $value = $('<div>', {
            "class": "value"
          });
          $watchers.append($watcher = $('<div>', {
            "class": "watching"
          }).attr('data-expr', watcher).append($name.text(watcher), $('<code>').text(': '), $value));
          this.code($value, value.toString(), [], true);
        } else {
          $watcher.find('.value code').remove();
          this.code($watcher.find('.value'), value.toString(), [], true);
        }
        $watcher.addClass('updated');
      }
      $watchers.find('.watching:not(.updated)').remove();
      return $watchers.find('.watching').removeClass('updated');
    };

    Wdb.prototype.ack = function() {
      return this.$eval.val('').trigger('autosize.resize');
    };

    Wdb.prototype.display = function(data) {
      var $tag, snippet;
      this.suggest_stop();
      snippet = this.$eval.val();
      this.code($('#scrollback'), data["for"], ['prompted']);
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
      $('#scrollback').append($tag);
      this.$eval.val('').prop('disabled', false).attr('data-index', -1).trigger('autosize.resize').focus();
      $('#completions').attr('style', '');
      this.termscroll();
      return this.chilling();
    };

    Wdb.prototype.searchback = function() {
      var h, index, re, val, _i, _len, _ref;
      this.suggest_stop();
      index = this.backsearch;
      val = this.$eval.val();
      _ref = this.cmd_hist;
      for (_i = 0, _len = _ref.length; _i < _len; _i++) {
        h = _ref[_i];
        re = new RegExp('(' + val + ')', 'gi');
        if (re.test(h)) {
          index--;
          if (index === 0) {
            $('#backsearch').html(h.replace(re, '<span class="backsearched">$1</span>'));
            return;
          }
        }
      }
      if (this.backsearch === 1) {
        this.searchback_stop();
        return;
      }
      return this.backsearch = Math.max(this.backsearch - 1, 1);
    };

    Wdb.prototype.searchback_stop = function(validate) {
      if (validate) {
        this.$eval.val($('#backsearch').text()).trigger('autosize.resize');
      }
      $('#backsearch').html('');
      return this.backsearch = null;
    };

    Wdb.prototype.die = function() {
      $('#source,#traceback').remove();
      $('h1').html('Dead<small>Program has exited</small>');
      this.ws.ws.close();
      return setTimeout((function() {
        return window.close();
      }), 10);
    };

    Wdb.prototype.register_handlers = function() {
      $('body,html').on('keydown', (function(_this) {
        return function(e) {
          var _ref;
          if ((_ref = _this.cm.cm) != null ? _ref._rw : void 0) {
            return true;
          }
          if ((e.ctrlKey && e.keyCode === 37) || e.keyCode === 119) {
            _this.ws.send('Continue');
          } else if ((e.ctrlKey && e.keyCode === 38) || e.keyCode === 120) {
            _this.ws.send('Return');
          } else if ((e.ctrlKey && e.keyCode === 39) || e.keyCode === 121) {
            _this.ws.send('Next');
          } else if ((e.ctrlKey && e.keyCode === 40) || e.keyCode === 122) {
            _this.ws.send('Step');
          } else if (e.keyCode === 118) {
            _this.ws.send('Until');
          } else {
            return true;
          }
          _this.working();
          return false;
        };
      })(this));
      this.$eval.on('keydown', (function(_this) {
        return function(e) {
          var $active, $tds, base, completion, endPos, filename, index, startPos, to_set, txtarea;
          if (e.altKey && e.keyCode === 82 && _this.backsearch) {
            _this.backsearch = Math.max(_this.backsearch - 1, 1);
            _this.searchback();
            return false;
          }
          if (e.ctrlKey) {
            if (e.keyCode === 82) {
              if (_this.backsearch === null) {
                _this.backsearch = 1;
              } else {
                if (e.shiftKey) {
                  _this.backsearch = Math.max(_this.backsearch - 1, 1);
                } else {
                  _this.backsearch++;
                }
              }
              _this.searchback();
              return false;
            } else if (e.keyCode === 67) {
              _this.searchback_stop();
            } else if (e.keyCode === 68) {
              _this.ws.send('Quit');
            } else {
              e.stopPropagation();
              return;
            }
          }
          if (e.keyCode === 13) {
            if (_this.backsearch) {
              _this.searchback_stop(true);
              return false;
            }
            if ($('#completions table td.active').length && !$('#completions table td.complete').length) {
              _this.suggest_stop();
              return false;
            }
            if (!e.shiftKey) {
              _this.execute(_this.$eval.val());
              return false;
            }
          } else if (e.keyCode === 27) {
            _this.suggest_stop();
            _this.searchback_stop();
            return false;
          } else if (e.keyCode === 9) {
            if (e.shiftKey) {
              txtarea = _this.$eval.get(0);
              startPos = txtarea.selectionStart;
              endPos = txtarea.selectionEnd;
              if (startPos || startPos === '0') {
                _this.$eval.val(_this.$eval.val().substring(0, startPos) + '  ' + _this.$eval.val().substring(endPos, _this.$eval.val().length)).trigger('autosize.resize');
              } else {
                _this.$eval.val(_this.$eval.val() + '  ').trigger('autosize.resize');
              }
              return false;
            }
            if (_this.backsearch) {
              return false;
            }
            $tds = $('#completions table td');
            $active = $tds.filter('.active');
            if ($tds.length) {
              if (!$active.length) {
                $active = $tds.first().addClass('active');
              } else {
                index = $tds.index($active);
                if (index === $tds.length - 1) {
                  index = 0;
                } else {
                  index++;
                }
                $active.removeClass('active complete');
                $active = $tds.eq(index).addClass('active');
              }
              base = $active.find('.base').text();
              completion = $active.find('.completion').text();
              _this.$eval.val($eval.data().root + base + completion).trigger('autosize.resize');
              $('#comp-desc').text($active.attr('title'));
              _this.termscroll();
            }
            return false;
          } else if (e.keyCode === 38) {
            filename = $('.selected .tracefile').text();
            if (!e.shiftKey) {
              index = parseInt(_this.$eval.attr('data-index')) + 1;
              if (index >= 0 && index < _this.cmd_hist.length) {
                to_set = _this.cmd_hist[index];
                if (index === 0) {
                  _this.$eval.attr('data-current', _this.$eval.val());
                }
                _this.$eval.val(to_set).attr('data-index', index).trigger('autosize.resize');
                _this.suggest_stop();
                _this.termscroll();
                return false;
              }
            }
          } else if (e.keyCode === 40) {
            filename = $('.selected .tracefile').text();
            if (!e.shiftKey) {
              index = parseInt($eval.attr('data-index')) - 1;
              if (index >= -1 && index < _this.cmd_hist.length) {
                if (index === -1) {
                  to_set = _this.$eval.attr('data-current');
                } else {
                  to_set = _this.cmd_hist[index];
                }
                _this.$eval.val(to_set).attr('data-index', index).trigger('autosize.resize');
                _this.suggest_stop();
                _this.termscroll();
                return false;
              }
            }
          }
        };
      })(this));
      $("#scrollback, #watchers").on('click', 'a.inspect', (function(_this) {
        return function(e) {
          _this.ws.send('Inspect', $(e.currentTarget).attr('href'));
          _this.working();
          return false;
        };
      })(this)).on('click', '.short.close', function() {
        return $(this).addClass('open').removeClass('close').next('.long').show('fast');
      }).on('click', '.long,.short.open', function() {
        var elt;
        elt = $(this).hasClass('long') ? $(this) : $(this).next('.long');
        return elt.hide('fast').prev('.short').removeClass('open').addClass('close');
      }).on('click', '.toggle', function() {
        return $(this).add($(this).next()).toggleClass('hidden', 'shown');
      });
      $("#watchers").on('click', '.watching .name', (function(_this) {
        return function(e) {
          _this.ws.send('Unwatch', $(e.currentTarget)).closest('.watching').attr('data-expr');
          return _this.working();
        };
      })(this));
      $("#source").on('mouseup', 'span', (function(_this) {
        return function(e) {
          var target;
          if (e.which === 2) {
            target = $(e.currentTarget).text().trim();
            _this.historize(target);
            _this.ws.send('Dump', target);
            return _this.working();
          }
        };
      })(this));
      $(document).on('keydown', (function(_this) {
        return function(e) {
          var sel;
          if (e.keyCode === 13) {
            sel = _this.cm.cm.getSelection().trim();
            if (sel) {
              _this.historize(sel);
              _this.ws.send('Eval', sel);
              return false;
            }
          }
        };
      })(this));
      return this.$eval.on('input', (function(_this) {
        return function(e) {
          var comp, hist, txt;
          txt = $(e.currentTarget).val();
          if (_this.backsearch) {
            if (!txt) {
              _this.searchback_stop();
            } else {
              _this.backsearch = 1;
              _this.searchback();
            }
            return;
          }
          hist = _this.session_cmd_hist[$('.selected .tracefile').text()] || [];
          if (txt && txt[0] !== '.') {
            comp = hist.slice(0).reverse().filter(function(e) {
              return e.indexOf('.') !== 0;
            }).join('\n') + '\n' + txt;
            if (_this.to_complete === null) {
              _this.ws.send('Complete', comp);
              return _this.to_complete = false;
            } else {
              return _this.to_complete = comp;
            }
          } else {
            return _this.suggest_stop();
          }
        };
      })(this)).on('blur', (function(_this) {
        return function() {
          return _this.searchback_stop();
        };
      })(this));
    };

    return Wdb;

  })(Log);

  $((function(_this) {
    return function() {
      setTimeout(function() {
        return $('#deactivate').click(function() {
          window.wdb.ws.send('Disable');
          return false;
        });
      }, 250);
      return _this.wdb = new Wdb();
    };
  })(this));

}).call(this);

//# sourceMappingURL=wdb.js.map
