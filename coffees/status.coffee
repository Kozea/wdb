ws = null
wait = 25

make_uuid_line = (uuid, socket) ->
  unless ($line = $(".sessions tr[data-uuid=#{uuid}]")).size()
    $line = $("<tr data-uuid=\"#{uuid}\">
      <td class=\"uuid\"><a href=\"/debug/session/#{uuid}\">#{uuid}</a></td>
      <td class=\"socket\">No</td>
      <td class=\"websocket\">No</td>
      <td class=\"close\"><a href=\"/uuid/#{uuid}/close\">Force close</a></td>
    ")
    $('.sessions tbody').append $line
  $line.find(".#{socket}").text('Yes')


rm_uuid_line = (uuid, socket) ->
  return unless ($line = $(".sessions tr[data-uuid=#{uuid}]")).size()
  if (socket is 'socket' and $line.find('.websocket').text() is 'No') or
     (socket is 'websocket' and $line.find('.socket').text() is 'No')
    $line.remove()
  else
    $line.find(".#{socket}").text('No')

make_brk_line = (data) ->
  brk = JSON.parse(data)
  line = '<tr>'
  for elt in ['fn', 'lno', 'cond', 'fun']
    line += "<td class=\"#{elt}\">#{brk[elt] or '∅'}</td>"
  line += "<td class=\"action\">
        <a href=\"/debug/file/#{ brk.fn }\"
          class=\"icon-open\">Open</a>
        <a href=\"\"
          class=\"icon-remove\">Remove</a>
      </td>"

  line += '</tr>'
  $('.breakpoints tbody').append $ line

rm_brk_line = (data) ->
  brk = JSON.parse(data)
  for tr in $('.breakpoints tr')
    $tr = $ tr
    same = true
    for elt in ['fn', 'lno', 'cond', 'fun']
      same = same and $tr.find(".#{elt}").text() is '' + (brk[elt] or '∅')
    if same
      $tr.remove()

ws_message = (event) ->
  wait = 25
  message = event.data
  pipe = message.indexOf('|')
  if pipe > -1
    cmd = message.substr(0, pipe)
    data = message.substr(pipe + 1)
  else
    cmd = message
    data = ''

  switch cmd
    when 'AddWebSocket'
      make_uuid_line data, 'websocket'
    when 'AddSocket'
      make_uuid_line data, 'socket'
    when 'RemoveWebSocket'
      rm_uuid_line data, 'websocket'
    when 'RemoveSocket'
      rm_uuid_line data, 'socket'
    when 'AddBreak'
      make_brk_line data
    when 'RemoveBreak'
      rm_brk_line data

create_socket = ->
  ws = new WebSocket "ws://#{location.host}/status"
  ws.onopen = ->
    console.log "WebSocket open", arguments
    $("tbody tr").remove()
    ws.send('ListSockets')
    ws.send('ListWebSockets')
    ws.send('ListBreaks')

  ws.onerror = ->
    console.log "WebSocket error", arguments

  ws.onmessage = ws_message
  ws.onclose = ->
    console.log "WebSocket closed", arguments
    wait *= 2
    setTimeout(create_socket, wait)

null_if_void = (s) ->
  if s is '∅'
    null
  else
    s

$ ->
  create_socket()
  $('.open-self')
    .click ->
      $.get('/self')
      return false

  $('.breakpoints tbody').on 'click', '.icon-remove', (e) ->
    $tr = $(this).closest('tr')
    brk =
      fn: $tr.find('.fn').text()
      lno: parseInt($tr.find('.lno').text())
      cond: null_if_void $tr.find('.cond').text()
      fun: null_if_void $tr.find('.fun').text()

    ws.send('RemoveBreak|' + JSON.stringify(brk))
    false
