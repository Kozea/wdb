(function() {
  var make_uuid_line, rm_uuid_line, ws_message;

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

  ws_message = function(event) {
    var cmd, data, message, pipe;
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
      case 'NEW_WS':
        return make_uuid_line(data, 'websocket');
      case 'NEW_S':
        return make_uuid_line(data, 'socket');
      case 'RM_WS':
        return rm_uuid_line(data, 'websocket');
      case 'RM_S':
        return rm_uuid_line(data, 'socket');
    }
  };

  $(function() {
    var ws;
    ws = new WebSocket("ws://" + location.host + "/status");
    ws.onopen = function() {
      return console.log("WebSocket open", arguments);
    };
    ws.onclose = function() {
      return console.log("WebSocket closed", arguments);
    };
    ws.onerror = function() {
      return console.log("WebSocket error", arguments);
    };
    ws.onmessage = ws_message;
    return $('.open-self').click(function() {
      $.get('/self');
      return false;
    });
  });

}).call(this);

//# sourceMappingURL=status.js.map
