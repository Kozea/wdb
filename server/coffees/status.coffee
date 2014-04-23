ws = null
wait = 25

make_uuid_line = (uuid, socket) ->
  unless ($line = $(".sessions tr[data-uuid=#{uuid}]")).size()
    $line = $("<tr data-uuid=\"#{uuid}\">
      <td class=\"uuid\"><a href=\"/debug/session/#{uuid}\">#{uuid}</a></td>
      <td class=\"socket\">No</td>
      <td class=\"websocket\">No</td>
      <td class=\"close\">
        <a class=\"fa fa-times-circle remove\" title=\"Force close\"></a>
      </td>
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

make_brk_line = (brk) ->
  line = '<tr>'
  for elt in ['fn', 'lno', 'cond', 'fun']
    line += "<td class=\"#{elt}\">#{brk[elt] or '∅'}</td>"
  line += "<td class=\"action\">
        <a class=\"fa fa-folder-open open\" title=\"Open\"></a>
        <a class=\"fa fa-minus-circle remove\" title=\"Remove\"></a>
      </td>"

  line += '</tr>'
  $('.breakpoints tbody').append $ line

rm_brk_line = (brk) ->
  for tr in $('.breakpoints tr')
    $tr = $ tr
    same = true
    for elt in ['fn', 'lno', 'cond', 'fun']
      same = same and $tr.find(".#{elt}").text() is '' + (brk[elt] or '∅')
    if same
      $tr.remove()

make_process_line = (proc) ->
  get_val = (elt) ->
    val = proc[elt]
    val = '∅' if not val?
    if elt is 'time'
      val = (new Date().getTime() / 1000) - val
      val = Math.round(val) + ' s'
    else if elt in ['mem', 'cpu']
      val = val.toFixed(2) + '%'
    val

  if ($tr = $(".processes tbody tr[data-pid=#{proc.pid}]")).size()
    for elt in ['pid', 'user', 'cmd', 'time', 'mem', 'cpu']
      $tr.find(".#{elt}").text(get_val elt)
  else
    line = "<tr data-pid=\"#{proc.pid}\"
    #{ if proc.threadof then 'data-threadof="' + proc.threadof + '"' else ''}>"
    for elt in ['pid', 'user', 'cmd', 'time', 'mem', 'cpu']
      line += "<td class=\"#{elt}\">#{get_val elt}</td>"
    line += "<td class=\"action\">"
    line += "<a href=\"\" class=\"fa fa-pause pause\" title=\"Pause\"></a> "
    if proc.threads > 1
      line += "<a href=\"\" class=\"fa fa-minus minus\"
        title=\"Toggle threads\"></a> "
    line += "</td>"

    line += '</tr>'
    $('.processes tbody').append $ line


ws_message = (event) ->
  wait = 25
  message = event.data
  pipe = message.indexOf('|')
  if pipe > -1
    cmd = message.substr(0, pipe)
    data = JSON.parse message.substr(pipe + 1)
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
    when 'AddProcess'
      make_process_line data
    when 'KeepProcess'
      for tr in $('.processes tbody tr')
        $tr = $ tr
        if parseInt($tr.attr('data-pid')) not in data
          $tr.remove()

    when 'StartLoop'
    # In case inotify is not available
      setInterval (->
        ws.send('ListProcesses')
      ), 2000

create_socket = ->
  ws = new WebSocket "ws://#{location.host}/status"
  ws.onopen = ->
    console.log "WebSocket open", arguments
    $("tbody tr").remove()
    ws.send('ListSockets')
    ws.send('ListWebSockets')
    ws.send('ListBreaks')
    ws.send('ListProcesses')

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
  $('.sessions tbody').on 'click', '.remove', (e) ->
    ws.send('RemoveUUID|' + $(this).closest('tr').attr('data-uuid'))
    false

  $('.breakpoints tbody').on 'click', '.open', (e) ->
    $tr = $(this).closest('tr')
    ws.send('RunFile|' + $tr.find('.fn').text())
    false

  $('.breakpoints tbody').on 'click', '.remove', (e) ->
    $tr = $(this).closest('tr')
    brk =
      fn: $tr.find('.fn').text()
      lno: parseInt($tr.find('.lno').text())
      cond: null_if_void $tr.find('.cond').text()
      fun: null_if_void $tr.find('.fun').text()

    ws.send('RemoveBreak|' + JSON.stringify(brk))
    false

  $('.processes tbody')
    .on('click', '.pause', (e) ->
      ws.send('Pause|' +  $(this).closest('tr').find('.pid').text())
      false)
    .on('click', '.minus', (e) ->
      $a = $(this)
      $tr = $a.closest('tr')
      $("[data-threadof=#{$tr.attr('data-pid')}]").hide 'fast'
      $a.attr 'class', $a.attr('class').replace(/minus/g, 'plus')
      false)
    .on('click', '.plus', (e) ->
      $a = $(this)
      $tr = $a.closest('tr')
      $("[data-threadof=#{$tr.attr('data-pid')}]").show 'fast'
      $a.attr 'class', $a.attr('class').replace(/plus/g, 'minus')
      false)

  $('.runfile').on 'submit', ->
    ws.send('RunFile|' + $(this).find('[type=text]').val())
    false
