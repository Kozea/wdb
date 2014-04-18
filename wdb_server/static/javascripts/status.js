(function() {
  var Log, create_socket, make_brk_line, make_process_line, make_uuid_line, null_if_void, rm_brk_line, rm_uuid_line, wait, ws, ws_message,
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

  make_process_line = function(proc) {
    var $tr, elt, get_val, line, _i, _j, _len, _len1, _ref, _ref1, _results;
    get_val = function(elt) {
      var val;
      val = proc[elt];
      if (val == null) {
        val = '∅';
      }
      if (elt === 'time') {
        val = (new Date().getTime() / 1000) - val;
        val = Math.round(val) + ' s';
      } else if (elt === 'mem' || elt === 'cpu') {
        val = val.toFixed(2) + '%';
      }
      return val;
    };
    if (($tr = $(".processes tbody tr[data-pid=" + proc.pid + "]")).size()) {
      _ref = ['pid', 'user', 'cmd', 'time', 'mem', 'cpu'];
      _results = [];
      for (_i = 0, _len = _ref.length; _i < _len; _i++) {
        elt = _ref[_i];
        _results.push($tr.find("." + elt).text(get_val(elt)));
      }
      return _results;
    } else {
      line = "<tr data-pid=\"" + proc.pid + "\" " + (proc.threadof ? 'data-threadof="' + proc.threadof + '"' : '') + ">";
      _ref1 = ['pid', 'user', 'cmd', 'time', 'mem', 'cpu'];
      for (_j = 0, _len1 = _ref1.length; _j < _len1; _j++) {
        elt = _ref1[_j];
        line += "<td class=\"" + elt + "\">" + (get_val(elt)) + "</td>";
      }
      line += "<td class=\"action\">";
      line += "<a href=\"\" class=\"fa fa-pause pause\" title=\"Pause\"></a> ";
      if (proc.threads > 1) {
        line += "<a href=\"\" class=\"fa fa-minus minus\" title=\"Toggle threads\"></a> ";
      }
      line += "</td>";
      line += '</tr>';
      return $('.processes tbody').append($(line));
    }
  };

  ws_message = function(event) {
    var $tr, cmd, data, message, pipe, tr, _i, _len, _ref, _ref1;
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
      case 'KeepProcess':
        _ref = $('.processes tbody tr');
        for (_i = 0, _len = _ref.length; _i < _len; _i++) {
          tr = _ref[_i];
          $tr = $(tr);
          if (_ref1 = parseInt($tr.attr('data-pid')), __indexOf.call(data, _ref1) < 0) {
            $tr.remove();
          }
        }
        return setTimeout((function() {
          return ws.send('ListProcesses');
        }), 1000);
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
      ws.send('Pause|' + $(this).closest('tr').find('.pid').text());
      return false;
    }).on('click', '.minus', function(e) {
      var $a, $tr;
      $a = $(this);
      $tr = $a.closest('tr');
      $("[data-threadof=" + ($tr.attr('data-pid')) + "]").hide('fast');
      $a.attr('class', $a.attr('class').replace(/minus/g, 'plus'));
      return false;
    }).on('click', '.plus', function(e) {
      var $a, $tr;
      $a = $(this);
      $tr = $a.closest('tr');
      $("[data-threadof=" + ($tr.attr('data-pid')) + "]").show('fast');
      $a.attr('class', $a.attr('class').replace(/plus/g, 'minus'));
      return false;
    });
    return $('.processes [type=button]').on('click', function(e) {
      return ws.send('RunFile|' + $(this).siblings('[type=text]').val());
    });
  });

}).call(this);

//# sourceMappingURL=status.js.map
