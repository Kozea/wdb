# This file is part of wdb
#
# wdb Copyright (c) 2012-2016  Florian Mounier, Kozea
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

ws = null
wait = 25

make_uuid_line = (uuid, socket, filename) ->
  filename = filename or ''
  unless ($line = $(".sessions tr[data-uuid=#{uuid}]")).length
    $line = $("<tr data-uuid=\"#{uuid}\">
      <td class=\"uuid mdl-data-table__cell--non-numeric\">
        <a href=\"/debug/session/#{uuid}\">#{uuid}</a>
      </td>
      <td class=\"socket mdl-data-table__cell--non-numeric\">No</td>
      <td class=\"websocket mdl-data-table__cell--non-numeric\">No</td>
      <td class=\"action\">
        <button class=\"mdl-button mdl-js-button mdl-button--icon close \
            mdl-button--colored\" title=\"Force close\">
          <i class=\"material-icons\">close</i>
        </button>
      </td>
    ")
    if $('.sessions .filename-head').length
      $line.prepend("
        <td class=\"filename mdl-data-table__cell--non-numeric\">
          <span>#{filename}</span>
        </td>
      ")
    $('.sessions tbody').append $line
  $line.find(".#{socket}").text('Yes')
  if filename
    $line.find('.filename span').text(filename)


rm_uuid_line = (uuid, socket) ->
  return unless ($line = $(".sessions tr[data-uuid=#{uuid}]")).length
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
      <button class=\"mdl-button mdl-js-button mdl-button--icon open \
          mdl-button--colored\" title=\"Open\">
        <i class=\"material-icons\">open_in_new</i>
      </button>
      <button class=\"mdl-button mdl-js-button mdl-button--icon delete \
          mdl-button--colored\" title=\"Remove\">
        <i class=\"material-icons\">delete</i>
      </button>
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
  if ($tr = $(".processes tbody tr[data-pid=#{proc.pid}]")).length
    for elt in ['pid', 'user', 'cmd', 'time', 'mem', 'cpu']
      $tr.find(".#{elt}").html(get_proc_thread_val proc, elt)
  else
    line = "<tr data-pid=\"#{proc.pid}\"
    #{ if proc.threadof then 'data-threadof="' + proc.threadof + '"' else ''}>"
    for elt in ['pid', 'user', 'cmd', 'time', 'mem', 'cpu']
      line += "<td class=\"rowspan #{elt}\">
        #{get_proc_thread_val proc, elt}</td>"
    line += """
      <td class=\"action\">
        <button class=\"mdl-button mdl-js-button mdl-button--icon plus \
          mdl-button--colored\" title=\"Toggle threads\">
          <i class=\"material-icons\">add</i>
        </button>
      </td>
      <td class=\"action\">
        <button class=\"mdl-button mdl-js-button mdl-button--icon pause \
          mdl-button--colored\" title=\"Pause\">
          <i class=\"material-icons\">pause</i>
        </button>
      </td>
    </tr>
    """
    $('.processes tbody').append $ line

make_thread_line = (thread) ->
  $proc = $(".processes tbody tr[data-pid=#{thread.of}]")
  return unless $proc.length

  if ($tr = $(".processes tbody tr[data-tid=#{thread.id}]")).length
    for elt in ['id', 'of']
      $tr.find(".#{elt}").text(get_proc_thread_val thread, elt)
  else
    line = """
      <tr data-tid=\"#{thread.id}\" data-of=\"#{thread.of}\"
        style="display: none">
        <td class=\"id\">#{get_proc_thread_val thread, 'id'}</td>
        <td class=\"action\">
          <button class=\"mdl-button mdl-js-button mdl-button--icon pause \
            mdl-button--colored\" title=\"Pause\">
            <i class=\"material-icons\">pause</i>
          </button>
        </td>
      </tr>
    """
    $next = $proc.nextAll('[data-pid]')
    if $next.length
      $next.before line
    else
      $(".processes tbody").append line
    # $proc.find('.rowspan').attr('rowspan',
    #   (+$proc.find('.rowspan').attr('rowspan') or 1) + 1)


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
      make_uuid_line data.uuid, 'socket', data.filename
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
  proto = if (document.location.protocol == "https:") then "wss:" else "ws:"
  ws = new WebSocket "#{proto}//#{location.host}/status"
  ws.onopen = ->
    $("tbody tr").remove()
    ws.send('ListSockets')
    ws.send('ListWebSockets')
    ws.send('ListBreaks')
    ws.send('ListProcesses')

  ws.onerror = ->

  ws.onmessage = ws_message
  ws.onclose = ->
    wait *= 2
    setTimeout(create_socket, wait)

null_if_void = (s) ->
  if s is '∅'
    null
  else
    s

$ ->
  create_socket()
  $('.sessions tbody').on 'click', '.close', (e) ->
    ws.send('RemoveUUID|' + $(this).closest('tr').attr('data-uuid'))
    false

  $('.breakpoints tbody').on 'click', '.open', (e) ->
    $tr = $(this).closest('tr')
    ws.send('RunFile|' + $tr.find('.fn').text())
    false

  $('.breakpoints tbody').on 'click', '.delete', (e) ->
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
      $button = $(this)
      $tr = $button.closest('tr')
      $("[data-of=#{$tr.attr('data-pid')}]").hide()
      $tr.find('.rowspan').attr 'rowspan', 1
      $button.removeClass('minus').addClass('plus').find('i').text 'add'
      false)
    .on('click', '.plus', (e) ->
      $button = $(this)
      $tr = $button.closest('tr')
      rowspan = $("[data-of=#{$tr.attr('data-pid')}]").show().length
      $tr.find('.rowspan').attr 'rowspan', rowspan + 1
      $button.removeClass('plus').addClass('minus').find('i').text 'remove'
      false)

  $('.runfile').on 'submit', ->
    ws.send('RunFile|' + $(this).find('[type=text]').val())
    false

  $('.open-shell button').on 'click', (e) ->
    ws.send 'RunShell'
