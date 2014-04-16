(function() {
  var Log, create_socket, make_brk_line, make_uuid_line, null_if_void, rm_brk_line, rm_uuid_line, wait, ws, ws_message;

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
      $line = $("<tr data-uuid=\"" + uuid + "\"> <td class=\"uuid\"><a href=\"/debug/session/" + uuid + "\">" + uuid + "</a></td> <td class=\"socket\">No</td> <td class=\"websocket\">No</td> <td class=\"close\"><a href=\"/uuid/" + uuid + "/close\">Force close</a></td>");
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

  make_brk_line = function(data) {
    var brk, elt, line, _i, _len, _ref;
    brk = JSON.parse(data);
    line = '<tr>';
    _ref = ['fn', 'lno', 'cond', 'fun'];
    for (_i = 0, _len = _ref.length; _i < _len; _i++) {
      elt = _ref[_i];
      line += "<td class=\"" + elt + "\">" + (brk[elt] || '∅') + "</td>";
    }
    line += "<td class=\"action\"> <a href=\"/debug/file/" + brk.fn + "\" class=\"icon-open\">Open</a> <a href=\"\" class=\"icon-remove\">Remove</a> </td>";
    line += '</tr>';
    return $('.breakpoints tbody').append($(line));
  };

  rm_brk_line = function(data) {
    var $tr, brk, elt, same, tr, _i, _j, _len, _len1, _ref, _ref1, _results;
    brk = JSON.parse(data);
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

  ws_message = function(event) {
    var cmd, data, message, pipe;
    wait = 25;
    message = event.data;
    pipe = message.indexOf('|');
    if (pipe > -1) {
      cmd = message.substr(0, pipe);
      data = message.substr(pipe + 1);
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
    }
  };

  create_socket = function() {
    ws = new WebSocket("ws://" + location.host + "/status");
    ws.onopen = function() {
      console.log("WebSocket open", arguments);
      $("tbody tr").remove();
      ws.send('ListSockets');
      ws.send('ListWebSockets');
      return ws.send('ListBreaks');
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
    $('.open-self').click(function() {
      $.get('/self');
      return false;
    });
    return $('.breakpoints tbody').on('click', '.icon-remove', function(e) {
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
  });

}).call(this);

//# sourceMappingURL=status.js.map
