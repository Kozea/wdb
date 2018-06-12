var Log, create_socket, get_proc_thread_val, make_brk_line, make_process_line, make_thread_line, make_uuid_line, null_if_void, rm_brk_line, rm_uuid_line, wait, ws, ws_message,
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

ws = null;

wait = 25;

make_uuid_line = function(uuid, socket, filename) {
  var $line;
  filename = filename || '';
  if (!($line = $(".sessions tr[data-uuid=" + uuid + "]")).length) {
    $line = $("<tr data-uuid=\"" + uuid + "\"> <td class=\"uuid mdl-data-table__cell--non-numeric\"> <a href=\"/debug/session/" + uuid + "\">" + uuid + "</a> </td> <td class=\"socket mdl-data-table__cell--non-numeric\">No</td> <td class=\"websocket mdl-data-table__cell--non-numeric\">No</td> <td class=\"action\"> <button class=\"mdl-button mdl-js-button mdl-button--icon close mdl-button--colored\" title=\"Force close\"> <i class=\"material-icons\">close</i> </button> </td>");
    if ($('.sessions .filename-head').length) {
      $line.prepend("<td class=\"filename mdl-data-table__cell--non-numeric\"> <span>" + filename + "</span> </td>");
    }
    $('.sessions tbody').append($line);
  }
  $line.find("." + socket).text('Yes');
  if (filename) {
    return $line.find('.filename span').text(filename);
  }
};

rm_uuid_line = function(uuid, socket) {
  var $line;
  if (!($line = $(".sessions tr[data-uuid=" + uuid + "]")).length) {
    return;
  }
  if ((socket === 'socket' && $line.find('.websocket').text() === 'No') || (socket === 'websocket' && $line.find('.socket').text() === 'No')) {
    return $line.remove();
  } else {
    return $line.find("." + socket).text('No');
  }
};

make_brk_line = function(brk) {
  var elt, i, len, line, ref;
  line = '<tr>';
  ref = ['fn', 'lno', 'cond', 'fun'];
  for (i = 0, len = ref.length; i < len; i++) {
    elt = ref[i];
    line += "<td class=\"" + elt + "\">" + (brk[elt] || '∅') + "</td>";
  }
  line += "<td class=\"action\"> <button class=\"mdl-button mdl-js-button mdl-button--icon open mdl-button--colored\" title=\"Open\"> <i class=\"material-icons\">open_in_new</i> </button> <button class=\"mdl-button mdl-js-button mdl-button--icon delete mdl-button--colored\" title=\"Remove\"> <i class=\"material-icons\">delete</i> </button> </td>";
  line += '</tr>';
  return $('.breakpoints tbody').append($(line));
};

rm_brk_line = function(brk) {
  var $tr, elt, i, j, len, len1, ref, ref1, results, same, tr;
  ref = $('.breakpoints tr');
  results = [];
  for (i = 0, len = ref.length; i < len; i++) {
    tr = ref[i];
    $tr = $(tr);
    same = true;
    ref1 = ['fn', 'lno', 'cond', 'fun'];
    for (j = 0, len1 = ref1.length; j < len1; j++) {
      elt = ref1[j];
      same = same && $tr.find("." + elt).text() === '' + (brk[elt] || '∅');
    }
    if (same) {
      results.push($tr.remove());
    } else {
      results.push(void 0);
    }
  }
  return results;
};

get_proc_thread_val = function(obj, elt) {
  var i, len, part, parts, ref, timeSince, val;
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
    ref = val.split(' ');
    for (i = 0, len = ref.length; i < len; i++) {
      part = ref[i];
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
  var $tr, elt, i, j, len, len1, line, ref, ref1, results;
  if (($tr = $(".processes tbody tr[data-pid=" + proc.pid + "]")).length) {
    ref = ['pid', 'user', 'cmd', 'time', 'mem', 'cpu'];
    results = [];
    for (i = 0, len = ref.length; i < len; i++) {
      elt = ref[i];
      results.push($tr.find("." + elt).html(get_proc_thread_val(proc, elt)));
    }
    return results;
  } else {
    line = "<tr data-pid=\"" + proc.pid + "\" " + (proc.threadof ? 'data-threadof="' + proc.threadof + '"' : '') + ">";
    ref1 = ['pid', 'user', 'cmd', 'time', 'mem', 'cpu'];
    for (j = 0, len1 = ref1.length; j < len1; j++) {
      elt = ref1[j];
      line += "<td class=\"rowspan " + elt + "\"> " + (get_proc_thread_val(proc, elt)) + "</td>";
    }
    line += "  <td class=\"action\">\n    <button class=\"mdl-button mdl-js-button mdl-button--icon plus mdl-button--colored\" title=\"Toggle threads\">\n      <i class=\"material-icons\">add</i>\n    </button>\n  </td>\n  <td class=\"action\">\n    <button class=\"mdl-button mdl-js-button mdl-button--icon pause mdl-button--colored\" title=\"Pause\">\n      <i class=\"material-icons\">pause</i>\n    </button>\n  </td>\n</tr>";
    return $('.processes tbody').append($(line));
  }
};

make_thread_line = function(thread) {
  var $next, $proc, $tr, elt, i, len, line, ref, results;
  $proc = $(".processes tbody tr[data-pid=" + thread.of + "]");
  if (!$proc.length) {
    return;
  }
  if (($tr = $(".processes tbody tr[data-tid=" + thread.id + "]")).length) {
    ref = ['id', 'of'];
    results = [];
    for (i = 0, len = ref.length; i < len; i++) {
      elt = ref[i];
      results.push($tr.find("." + elt).text(get_proc_thread_val(thread, elt)));
    }
    return results;
  } else {
    line = "<tr data-tid=\"" + thread.id + "\" data-of=\"" + thread.of + "\"\n  style=\"display: none\">\n  <td class=\"id\">" + (get_proc_thread_val(thread, 'id')) + "</td>\n  <td class=\"action\">\n    <button class=\"mdl-button mdl-js-button mdl-button--icon pause mdl-button--colored\" title=\"Pause\">\n      <i class=\"material-icons\">pause</i>\n    </button>\n  </td>\n</tr>";
    $next = $proc.nextAll('[data-pid]');
    if ($next.length) {
      return $next.before(line);
    } else {
      return $(".processes tbody").append(line);
    }
  }
};

ws_message = function(event) {
  var $proc, $tr, cmd, data, i, j, len, len1, message, pipe, ref, ref1, ref2, ref3, results, results1, tr;
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
      return make_uuid_line(data.uuid, 'socket', data.filename);
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
      ref = $('.processes tbody tr[data-pid]');
      results = [];
      for (i = 0, len = ref.length; i < len; i++) {
        tr = ref[i];
        $tr = $(tr);
        if (ref1 = parseInt($tr.attr('data-pid')), indexOf.call(data, ref1) < 0) {
          $(".processes [data-of=" + ($tr.attr('data-pid')) + "]").remove();
          results.push($tr.remove());
        } else {
          results.push(void 0);
        }
      }
      return results;
      break;
    case 'KeepProcess':
      ref2 = $('.processes tbody tr[data-tid]');
      results1 = [];
      for (j = 0, len1 = ref2.length; j < len1; j++) {
        tr = ref2[j];
        $tr = $(tr);
        if (ref3 = parseInt($tr.attr('data-tid')), indexOf.call(data, ref3) < 0) {
          $tr.remove();
          $proc = $(".processes [data-pid=" + ($tr.attr('data-of')) + "]");
          results1.push($proc.attr('rowspan', +$proc.attr('rowspan') - 1));
        } else {
          results1.push(void 0);
        }
      }
      return results1;
      break;
    case 'StartLoop':
      return setInterval((function() {
        return ws.send('ListProcesses');
      }), 2000);
  }
};

create_socket = function() {
  var proto;
  proto = document.location.protocol === "https:" ? "wss:" : "ws:";
  ws = new WebSocket(proto + "//" + location.host + "/status");
  ws.onopen = function() {
    $("tbody tr").remove();
    ws.send('ListSockets');
    ws.send('ListWebSockets');
    ws.send('ListBreaks');
    return ws.send('ListProcesses');
  };
  ws.onerror = function() {};
  ws.onmessage = ws_message;
  return ws.onclose = function() {
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
  $('.sessions tbody').on('click', '.close', function(e) {
    ws.send('RemoveUUID|' + $(this).closest('tr').attr('data-uuid'));
    return false;
  });
  $('.breakpoints tbody').on('click', '.open', function(e) {
    var $tr;
    $tr = $(this).closest('tr');
    ws.send('RunFile|' + $tr.find('.fn').text());
    return false;
  });
  $('.breakpoints tbody').on('click', '.delete', function(e) {
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
    var $button, $tr;
    $button = $(this);
    $tr = $button.closest('tr');
    $("[data-of=" + ($tr.attr('data-pid')) + "]").hide();
    $tr.find('.rowspan').attr('rowspan', 1);
    $button.removeClass('minus').addClass('plus').find('i').text('add');
    return false;
  }).on('click', '.plus', function(e) {
    var $button, $tr, rowspan;
    $button = $(this);
    $tr = $button.closest('tr');
    rowspan = $("[data-of=" + ($tr.attr('data-pid')) + "]").show().length;
    $tr.find('.rowspan').attr('rowspan', rowspan + 1);
    $button.removeClass('plus').addClass('minus').find('i').text('remove');
    return false;
  });
  $('.runfile').on('submit', function() {
    ws.send('RunFile|' + $(this).find('[type=text]').val());
    return false;
  });
  return $('.open-shell button').on('click', function(e) {
    return ws.send('RunShell');
  });
});
