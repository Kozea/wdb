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

get_proc_thread_val = (obj, elt) ->
  val = obj[elt]
  if not val?
    return '∅'
  if elt is 'time'
    timeSince = (date) ->
      seconds = Math.floor((new Date() - date) / 1000)
      interval = Math.floor(seconds / 31536000)
      return interval + "y"  if interval > 1
      interval = Math.floor(seconds / 2592000)
      return interval + "mo"  if interval > 1
      interval = Math.floor(seconds / 86400)
      return interval + "d"  if interval > 1
      interval = Math.floor(seconds / 3600)
      return interval + "h"  if interval > 1
      interval = Math.floor(seconds / 60)
      return interval + "m"  if interval > 1
      Math.floor(seconds) + "s"

    val = timeSince 1000 * val
  else if elt in ['mem', 'cpu']
    val = val.toFixed(2) + '%'
  else if elt is 'cmd'
    parts = []
    for part in val.split(' ')
      if part.indexOf('/') is 0
        parts.push "<abbr title=\"#{part}\">#{part.split('/').slice(-1)}</abbr>"
      else if part.indexOf(':') is 1 and part.indexOf('\\') is 2
        parts.push "<abbr title=\"#{part}\">
          #{part.slice(3).split('\\').slice(-1)}</abbr>"
      else
        parts.push part
    val = parts.join(' ')
  val

make_process_line = (proc) ->
  if ($tr = $(".processes tbody tr[data-pid=#{proc.pid}]")).size()
    for elt in ['pid', 'user', 'cmd', 'time', 'mem', 'cpu']
      $tr.find(".#{elt}").html(get_proc_thread_val proc, elt)
  else
    line = "<tr data-pid=\"#{proc.pid}\"
    #{ if proc.threadof then 'data-threadof="' + proc.threadof + '"' else ''}>"
    for elt in ['pid', 'user', 'cmd', 'time', 'mem', 'cpu']
      line += "<td class=\"rowspan #{elt}\">
        #{get_proc_thread_val proc, elt}</td>"
    line += "<td class=\"action\"><a href=\"\" class=\"fa fa-minus minus\"
        title=\"Toggle threads\"></a></td>"
    line += "<td class=\"action\">"
    line += "<a href=\"\" class=\"fa fa-pause pause\" title=\"Pause\"></a> "
    line += "</td>"
    line += '</tr>'
    $('.processes tbody').append $ line

make_thread_line = (thread) ->
  $proc = $(".processes tbody tr[data-pid=#{thread.of}]")
  return unless $proc.size()

  if ($tr = $(".processes tbody tr[data-tid=#{thread.id}]")).size()
    for elt in ['id', 'of']
      $tr.find(".#{elt}").text(get_proc_thread_val thread, elt)
  else
    line = "<tr data-tid=\"#{thread.id}\" data-of=\"#{thread.of}\">"

    line += "<td class=\"id\">#{get_proc_thread_val thread, 'id'}</td>"
    line += "<td class=\"action\">"
    line += "<a href=\"\" class=\"fa fa-pause pause\" title=\"Pause\"></a> "
    line += "</td>"

    line += '</tr>'
    $next = $proc.nextAll('[data-pid]')
    if $next.size()
      $next.before line
    else
      $(".processes tbody").append line
    $proc.find('.rowspan').attr('rowspan',
      (+$proc.find('.rowspan').attr('rowspan') or 1) + 1)


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
    when 'AddThread'
      make_thread_line data
    when 'KeepProcess'
      for tr in $('.processes tbody tr[data-pid]')
        $tr = $ tr
        if parseInt($tr.attr('data-pid')) not in data
          $(".processes [data-of=#{$tr.attr('data-pid')}]").remove()
          $tr.remove()

    when 'KeepProcess'
      for tr in $('.processes tbody tr[data-tid]')
        $tr = $ tr
        if parseInt($tr.attr('data-tid')) not in data
          $tr.remove()
          $proc = $(".processes [data-pid=#{$tr.attr('data-of')}]")
          $proc.attr('rowspan', +$proc.attr('rowspan') - 1)

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
      $tr = $(this).closest('tr')
      ws.send('Pause|' + ($tr.attr('data-pid') or $tr.attr('data-tid')))
      false)
    .on('click', '.minus', (e) ->
      $a = $(this)
      $tr = $a.closest('tr')
      $("[data-of=#{$tr.attr('data-pid')}]").hide()
      $tr.find('.rowspan').attr 'rowspan', 1
      $a.attr 'class', $a.attr('class').replace(/minus/g, 'plus')
      false)
    .on('click', '.plus', (e) ->
      $a = $(this)
      $tr = $a.closest('tr')
      rowspan = $("[data-of=#{$tr.attr('data-pid')}]").show().size()
      $tr.find('.rowspan').attr 'rowspan', rowspan + 1
      $a.attr 'class', $a.attr('class').replace(/plus/g, 'minus')
      false)

  $('.runfile').on 'submit', ->
    ws.send('RunFile|' + $(this).find('[type=text]').val())
    false
