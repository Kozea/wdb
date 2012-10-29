$ =>
    @ajaws = true
    $.ajax(location.href,
        headers:
            "W-Type": 'Get'
    ).done((data) =>
        @ajaws = false
        # $('body').replaceWith(data);
        document.open()
        document.write data
        document.close()
    ).fail (data) =>
        @ajaws = false
        # $('body').replaceWith(data.responseText);
        document.open()
        document.write data.responseText
        document.close()

    @ws = ws = new WebSocket "ws://localhost:" + @__ws_port
    ws.onclose = (m) -> console.log "close #{m}"
    ws.onmessage = (m) =>
        @__w = JSON.parse m.data
        $('body').html('')
        w_load()
    ws.onerror = (m) -> console.log "error #{m}"
    ws.onopen = (m) ->
        console.log "open #{m}"
        # ws.close()

    @onbeforeunload = ->
        try
            ws.send('QUIT')
        catch e
            {}
        undefined
