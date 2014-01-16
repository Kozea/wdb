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
    if (socket is 'socket' and $line.find('.websocket').text() is 'No') or (socket is 'websocket' and $line.find('.socket').text() is 'No')
        $line.remove()
    else
        $line.find(".#{socket}").text('No')

ws_message = (event) ->
    message = event.data
    pipe = message.indexOf('|')
    if pipe > -1
        cmd = message.substr(0, pipe)
        data = message.substr(pipe + 1)
    else
        cmd = message
        data = ''

    switch cmd
        when 'NEW_WS'
            make_uuid_line data, 'websocket'
        when 'NEW_S'
            make_uuid_line data, 'socket'
        when 'RM_WS'
            rm_uuid_line data, 'websocket'
        when 'RM_S'
            rm_uuid_line data, 'socket'

$ ->
    ws = new WebSocket "ws://#{location.host}/status"
    ws.onopen = -> console.log "WebSocket open", arguments
    ws.onclose = -> console.log "WebSocket closed", arguments
    ws.onerror = -> console.log "WebSocket error", arguments
    ws.onmessage = ws_message

    $('.open-self')
        .click ->
            $.get('/self')
            return false
