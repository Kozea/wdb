$ =>
    $.ajax(location.href,
        data:
            __h__: "__at__"
    ).done((data) ->
        document.open()
        document.write data
        document.close()
    ).fail (data) ->
        document.open()
        document.write data.responseText
        document.close()

    @ws = ws = new WebSocket "ws://localhost:" + @__ws_port
    ws.onclose = (m) -> console.log "close #{m}"
    ws.onmessage = (m) -> console.log "message #{m.data}"
    ws.onerror = (m) -> console.log "error #{m}"
    ws.onopen = (m) ->
        console.log "open #{m}"
        # ws.close()

