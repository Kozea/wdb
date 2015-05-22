var Log;

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

$(function() {
  var $code, $trace, code, file, fun, i, len, lno, ref, ref1, results;
  $('#activate').click(function() {
    $.get('/__wdb/on').done(function() {
      return location.reload(true);
    });
    return false;
  });
  $('#title').text(_title).append($('<small>').text(_subtitle));
  if (trace.trace) {
    $('#wdb').append($trace = $('<article>', {
      "class": 'trace_500'
    }));
    ref = trace.trace;
    results = [];
    for (i = 0, len = ref.length; i < len; i++) {
      ref1 = ref[i], file = ref1[0], lno = ref1[1], fun = ref1[2], code = ref1[3];
      $trace.append($('<div>', {
        "class": 'traceline'
      }).append($('<div>', {
        "class": 'flno'
      }).text('File ' + file + ':' + lno), $('<div>', {
        "class": 'fun'
      }).text(fun), $code = $('<code>', {
        "class": 'cm'
      })));
      results.push(CodeMirror.runMode(code || ' ', "python", $code.get(0)));
    }
    return results;
  }
});
