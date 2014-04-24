(function() {
  var Log, create_socket, get_proc_thread_val, make_brk_line, make_process_line, make_thread_line, make_uuid_line, null_if_void, rm_brk_line, rm_uuid_line, wait, ws, ws_message,
    __indexOf = [].indexOf || function(item) { for (var i = 0, l = this.length; i < l; i++) { if (i in this && this[i] === item) return i; } return -1; };

  Log = (function() {
    function Log() {
      this.debug = $('body').attr('data-debug') || false;
    }

    Log.prototype.log = function() {
      var log_args, name;
      if (this.debug) {
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

  ws = null;

  wait = 25;

  make_uuid_line = function(uuid, socket) {
    var $line;
    if (!($line = $(".sessions tr[data-uuid=" + uuid + "]")).size()) {
      $line = $("<tr data-uuid=\"" + uuid + "\"> <td class=\"uuid\"><a href=\"/debug/session/" + uuid + "\">" + uuid + "</a></td> <td class=\"socket\">No</td> <td class=\"websocket\">No</td> <td class=\"close\"> <a class=\"fa fa-times-circle remove\" title=\"Force close\"></a> </td>");
      $('.sessions tbody').append($line);
    }
    return $line.find("." + socket).text('Yes');
  };

  rm_uuid_line = function(uuid, socket) {
    var $line;
    if (!($line = $(".sessions tr[data-uuid=" + uuid + "]")).size()) {
      return;
    }
    if ((socket === 'socket' && $line.find('.websocket').text() === 'No') || (socket === 'websocket' && $line.find('.socket').text() === 'No')) {
      return $line.remove();
    } else {
      return $line.find("." + socket).text('No');
    }
  };

  make_brk_line = function(brk) {
    var elt, line, _i, _len, _ref;
    line = '<tr>';
    _ref = ['fn', 'lno', 'cond', 'fun'];
    for (_i = 0, _len = _ref.length; _i < _len; _i++) {
      elt = _ref[_i];
      line += "<td class=\"" + elt + "\">" + (brk[elt] || '∅') + "</td>";
    }
    line += "<td class=\"action\"> <a class=\"fa fa-folder-open open\" title=\"Open\"></a> <a class=\"fa fa-minus-circle remove\" title=\"Remove\"></a> </td>";
    line += '</tr>';
    return $('.breakpoints tbody').append($(line));
  };

  rm_brk_line = function(brk) {
    var $tr, elt, same, tr, _i, _j, _len, _len1, _ref, _ref1, _results;
    _ref = $('.breakpoints tr');
    _results = [];
    for (_i = 0, _len = _ref.length; _i < _len; _i++) {
      tr = _ref[_i];
      $tr = $(tr);
      same = true;
      _ref1 = ['fn', 'lno', 'cond', 'fun'];
      for (_j = 0, _len1 = _ref1.length; _j < _len1; _j++) {
        elt = _ref1[_j];
        same = same && $tr.find("." + elt).text() === '' + (brk[elt] || '∅');
      }
      if (same) {
        _results.push($tr.remove());
      } else {
        _results.push(void 0);
      }
    }
    return _results;
  };

  get_proc_thread_val = function(obj, elt) {
    var part, parts, timeSince, val, _i, _len, _ref;
    val = obj[elt];
    if (val == null) {
      return '∅';
    }
    if (elt === 'time') {
      timeSince = function(date) {
        var interval, seconds;
        seconds = Math.floor((new Date() - date) / 1000);
        interval = Math.floor(seconds / 31536000);
        if (interval > 1) {
          return interval + "y";
        }
        interval = Math.floor(seconds / 2592000);
        if (interval > 1) {
          return interval + "mo";
        }
        interval = Math.floor(seconds / 86400);
        if (interval > 1) {
          return interval + "d";
        }
        interval = Math.floor(seconds / 3600);
        if (interval > 1) {
          return interval + "h";
        }
        interval = Math.floor(seconds / 60);
        if (interval > 1) {
          return interval + "m";
        }
        return Math.floor(seconds) + "s";
      };
      val = timeSince(1000 * val);
    } else if (elt === 'mem' || elt === 'cpu') {
      val = val.toFixed(2) + '%';
    } else if (elt === 'cmd') {
      parts = [];
      _ref = val.split(' ');
      for (_i = 0, _len = _ref.length; _i < _len; _i++) {
        part = _ref[_i];
        if (part.indexOf('/') === 0) {
          parts.push("<abbr title=\"" + part + "\">" + (part.split('/').slice(-1)) + "</abbr>");
        } else if (part.indexOf(':') === 1 && part.indexOf('\\') === 2) {
          parts.push("<abbr title=\"" + part + "\"> " + (part.slice(3).split('\\').slice(-1)) + "</abbr>");
        } else {
          parts.push(part);
        }
      }
      val = parts.join(' ');
    }
    return val;
  };

  make_process_line = function(proc) {
    var $tr, elt, line, _i, _j, _len, _len1, _ref, _ref1, _results;
    if (($tr = $(".processes tbody tr[data-pid=" + proc.pid + "]")).size()) {
      _ref = ['pid', 'user', 'cmd', 'time', 'mem', 'cpu'];
      _results = [];
      for (_i = 0, _len = _ref.length; _i < _len; _i++) {
        elt = _ref[_i];
        _results.push($tr.find("." + elt).html(get_proc_thread_val(proc, elt)));
      }
      return _results;
    } else {
      line = "<tr data-pid=\"" + proc.pid + "\" " + (proc.threadof ? 'data-threadof="' + proc.threadof + '"' : '') + ">";
      _ref1 = ['pid', 'user', 'cmd', 'time', 'mem', 'cpu'];
      for (_j = 0, _len1 = _ref1.length; _j < _len1; _j++) {
        elt = _ref1[_j];
        line += "<td class=\"rowspan " + elt + "\"> " + (get_proc_thread_val(proc, elt)) + "</td>";
      }
      line += "<td class=\"action\"><a href=\"\" class=\"fa fa-minus minus\" title=\"Toggle threads\"></a></td>";
      line += "<td class=\"action\">";
      line += "<a href=\"\" class=\"fa fa-pause pause\" title=\"Pause\"></a> ";
      line += "</td>";
      line += '</tr>';
      return $('.processes tbody').append($(line));
    }
  };

  make_thread_line = function(thread) {
    var $next, $proc, $tr, elt, line, _i, _len, _ref, _results;
    $proc = $(".processes tbody tr[data-pid=" + thread.of + "]");
    if (!$proc.size()) {
      return;
    }
    if (($tr = $(".processes tbody tr[data-tid=" + thread.id + "]")).size()) {
      _ref = ['id', 'of'];
      _results = [];
      for (_i = 0, _len = _ref.length; _i < _len; _i++) {
        elt = _ref[_i];
        _results.push($tr.find("." + elt).text(get_proc_thread_val(thread, elt)));
      }
      return _results;
    } else {
      line = "<tr data-tid=\"" + thread.id + "\" data-of=\"" + thread.of + "\">";
      line += "<td class=\"id\">" + (get_proc_thread_val(thread, 'id')) + "</td>";
      line += "<td class=\"action\">";
      line += "<a href=\"\" class=\"fa fa-pause pause\" title=\"Pause\"></a> ";
      line += "</td>";
      line += '</tr>';
      $next = $proc.nextAll('[data-pid]');
      if ($next.size()) {
        $next.before(line);
      } else {
        $(".processes tbody").append(line);
      }
      return $proc.find('.rowspan').attr('rowspan', (+$proc.find('.rowspan').attr('rowspan') || 1) + 1);
    }
  };

  ws_message = function(event) {
    var $proc, $tr, cmd, data, message, pipe, tr, _i, _j, _len, _len1, _ref, _ref1, _ref2, _ref3, _results, _results1;
    wait = 25;
    message = event.data;
    pipe = message.indexOf('|');
    if (pipe > -1) {
      cmd = message.substr(0, pipe);
      data = JSON.parse(message.substr(pipe + 1));
    } else {
      cmd = message;
      data = '';
    }
    switch (cmd) {
      case 'AddWebSocket':
        return make_uuid_line(data, 'websocket');
      case 'AddSocket':
        return make_uuid_line(data, 'socket');
      case 'RemoveWebSocket':
        return rm_uuid_line(data, 'websocket');
      case 'RemoveSocket':
        return rm_uuid_line(data, 'socket');
      case 'AddBreak':
        return make_brk_line(data);
      case 'RemoveBreak':
        return rm_brk_line(data);
      case 'AddProcess':
        return make_process_line(data);
      case 'AddThread':
        return make_thread_line(data);
      case 'KeepProcess':
        _ref = $('.processes tbody tr[data-pid]');
        _results = [];
        for (_i = 0, _len = _ref.length; _i < _len; _i++) {
          tr = _ref[_i];
          $tr = $(tr);
          if (_ref1 = parseInt($tr.attr('data-pid')), __indexOf.call(data, _ref1) < 0) {
            $(".processes [data-of=" + ($tr.attr('data-pid')) + "]").remove();
            _results.push($tr.remove());
          } else {
            _results.push(void 0);
          }
        }
        return _results;
        break;
      case 'KeepProcess':
        _ref2 = $('.processes tbody tr[data-tid]');
        _results1 = [];
        for (_j = 0, _len1 = _ref2.length; _j < _len1; _j++) {
          tr = _ref2[_j];
          $tr = $(tr);
          if (_ref3 = parseInt($tr.attr('data-tid')), __indexOf.call(data, _ref3) < 0) {
            $tr.remove();
            $proc = $(".processes [data-pid=" + ($tr.attr('data-of')) + "]");
            _results1.push($proc.attr('rowspan', +$proc.attr('rowspan') - 1));
          } else {
            _results1.push(void 0);
          }
        }
        return _results1;
        break;
      case 'StartLoop':
        return setInterval((function() {
          return ws.send('ListProcesses');
        }), 2000);
    }
  };

  create_socket = function() {
    ws = new WebSocket("ws://" + location.host + "/status");
    ws.onopen = function() {
      console.log("WebSocket open", arguments);
      $("tbody tr").remove();
      ws.send('ListSockets');
      ws.send('ListWebSockets');
      ws.send('ListBreaks');
      return ws.send('ListProcesses');
    };
    ws.onerror = function() {
      return console.log("WebSocket error", arguments);
    };
    ws.onmessage = ws_message;
    return ws.onclose = function() {
      console.log("WebSocket closed", arguments);
      wait *= 2;
      return setTimeout(create_socket, wait);
    };
  };

  null_if_void = function(s) {
    if (s === '∅') {
      return null;
    } else {
      return s;
    }
  };

  $(function() {
    create_socket();
    $('.sessions tbody').on('click', '.remove', function(e) {
      ws.send('RemoveUUID|' + $(this).closest('tr').attr('data-uuid'));
      return false;
    });
    $('.breakpoints tbody').on('click', '.open', function(e) {
      var $tr;
      $tr = $(this).closest('tr');
      ws.send('RunFile|' + $tr.find('.fn').text());
      return false;
    });
    $('.breakpoints tbody').on('click', '.remove', function(e) {
      var $tr, brk;
      $tr = $(this).closest('tr');
      brk = {
        fn: $tr.find('.fn').text(),
        lno: parseInt($tr.find('.lno').text()),
        cond: null_if_void($tr.find('.cond').text()),
        fun: null_if_void($tr.find('.fun').text())
      };
      ws.send('RemoveBreak|' + JSON.stringify(brk));
      return false;
    });
    $('.processes tbody').on('click', '.pause', function(e) {
      var $tr;
      $tr = $(this).closest('tr');
      ws.send('Pause|' + ($tr.attr('data-pid') || $tr.attr('data-tid')));
      return false;
    }).on('click', '.minus', function(e) {
      var $a, $tr;
      $a = $(this);
      $tr = $a.closest('tr');
      $("[data-of=" + ($tr.attr('data-pid')) + "]").hide();
      $tr.find('.rowspan').attr('rowspan', 1);
      $a.attr('class', $a.attr('class').replace(/minus/g, 'plus'));
      return false;
    }).on('click', '.plus', function(e) {
      var $a, $tr, rowspan;
      $a = $(this);
      $tr = $a.closest('tr');
      rowspan = $("[data-of=" + ($tr.attr('data-pid')) + "]").show().size();
      $tr.find('.rowspan').attr('rowspan', rowspan + 1);
      $a.attr('class', $a.attr('class').replace(/plus/g, 'minus'));
      return false;
    });
    return $('.runfile').on('submit', function() {
      ws.send('RunFile|' + $(this).find('[type=text]').val());
      return false;
    });
  });

}).call(this);

//# sourceMappingURL=status.js.map
