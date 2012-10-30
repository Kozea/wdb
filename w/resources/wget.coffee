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
        pipe = m.data.indexOf('|')
        if pipe > -1
            cmd = m.data.substr(0, pipe)
            data = m.data.substr(pipe + 1)
        else
            cmd = m.data

        switch cmd
            when 'TRACE'
                @__w = JSON.parse data
                $('body').html('')
                w_load()
            when 'PING'
                ws.send('PONG')
            when 'JSON'
                @_done(JSON.parse(data))
                @_done = null
                
    ws.onerror = (m) -> console.log "WebSocket error", m
    ws.onopen = (m) ->
        console.log "WebSocket is open", m

    @onbeforeunload = ->
        try
            ws.send('QUIT')
        catch e
            {}
        undefined
