(function() {
  var Log;

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

  $(function() {
    var $code, $trace, code, file, fun, lno, _i, _len, _ref, _ref1, _results;
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
      _ref = trace.trace;
      _results = [];
      for (_i = 0, _len = _ref.length; _i < _len; _i++) {
        _ref1 = _ref[_i], file = _ref1[0], lno = _ref1[1], fun = _ref1[2], code = _ref1[3];
        $trace.append($('<div>', {
          "class": 'traceline'
        }).append($('<div>', {
          "class": 'flno'
        }).text('File ' + file + ':' + lno), $('<div>', {
          "class": 'fun'
        }).text(fun), $code = $('<code>', {
          "class": 'cm'
        })));
        _results.push(CodeMirror.runMode(code || ' ', "python", $code.get(0)));
      }
      return _results;
    }
  });

}).call(this);

//# sourceMappingURL=500.js.map
