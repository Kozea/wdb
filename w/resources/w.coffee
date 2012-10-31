#### Initializations ####

file_cache = {}
ws = null
persistable = 'localStorage' of window and window.localStorage
if persistable and localStorage['__w_cmd_hist']
    try
        cmd_hist = JSON.parse localStorage['__w_cmd_hist']
    catch e
        cmd_hist = {}
else
    cmd_hist = {}

persist = ->
    if not persistable
        return
    localStorage['__w_cmd_hist'] = JSON.stringify cmd_hist

$.SyntaxHighlighter.loadedExtras = true
$.SyntaxHighlighter.init(
    debug: true,
    lineNumbers: false,
    highlight: false,
    load: false)


#### Loading ####
$ =>
    # Try getting the original page
    $.ajax(location.href,
        headers:
            "W-Type": 'Get'
    ).done((data) =>
        document.open()
        document.write data
        document.close()
    ).fail (data) =>
        document.open()
        document.write data.responseText
        document.close()

    # Open a websocket in case of request break
    @_ws = ws = new WebSocket "ws://localhost:" + @__ws_port
    ws.onclose = (m) -> console.log "close #{m}"
    ws.onerror = (m) -> console.log "WebSocket error", m
    
    ws.onopen = (m) ->
        # We are connected, ie: in request break
        console.log "WebSocket is open", m
        # Start by getting current trace
        register_eval()
        ws.send('Start')

    ws.onmessage = (m) =>
        # Open a websocket in case of request break
        pipe = m.data.indexOf('|')
        if pipe > -1
            cmd = m.data.substr(0, pipe)
            data = JSON.parse m.data.substr(pipe + 1)
        else
            cmd = m.data
        console.log cmd
        switch cmd
            when 'Title'  then title data
            when 'Trace'  then trace data
            when 'File'   then file data
            when 'Select' then select data
            when 'Print'  then print data
            when 'Echo'   then echo data
            when 'Ping'   then ws.send('Pong')

    @onbeforeunload = ->
        try
            ws.send('Quit')
        catch e
            {}
        undefined

title = (data) ->
    $('#title').text(data.title).append($('<small>').text(data.subtitle))
    $('#source').css(height: $(window).height() - $('#title').outerHeight(true))
    $('#traceback').css(height: $(window).height() - $('#title').outerHeight(true))

trace = (data) ->
    $('#traceback').empty()
    for frame in data.trace
        $traceline = $('<div>')
            .addClass('traceline')
            .attr('id', 'trace-' + frame.level)
            .attr('data-level', frame.level)

        $tracefile = $('<span>').addClass('tracefile').text(frame.file)
        $tracelno = $('<span>').addClass('tracelno').text(frame.lno)
        $tracefun = $('<span>').addClass('tracefun').text(frame.function)

        $tracefilelno = $('<div>')
            .addClass('tracefilelno')
            .append($tracefile)
            .append($tracelno)

        $tracefunfun = $('<div>')
            .addClass('tracefunfun')
            .append($tracefun)

        if frame.file.indexOf('site-packages') > 0
            suffix = frame.file.split('site-packages').slice(-1)[0]
            $tracefile.text(suffix)
            $tracefile.prepend($('<span>').addClass('tracestar').text('*').attr(title: frame.file))

        $tracecode = $('<div>')
            .addClass('tracecode')
            .append(code(frame.code))

        $traceline.append $tracefilelno
        $traceline.append $tracecode
        $traceline.append $tracefunfun
        $('#traceback').prepend $traceline
    $('.traceline').each(->
        $(@).find('code').syntaxHighlight()
    ).on('click', ->
        ws.send('Select|' + $(@).attr('data-level'))
    )

file = (data) ->
    $('#sourcecode').empty().append nh = code(data.file, ['linenums'])
    nh.syntaxHighlight()
    $('#sourcecode').attr('title', data.name)
    file_cache[data.name] = $('#sourcecode').html()

select = (data) ->
    current_frame = data.frame
    if current_frame.file not of file_cache
        ws.send("File")
        return
    $('.traceline').removeClass('selected')
    # $traceline.addClass('current')
    $('#trace-' + current_frame.level).addClass('selected')
    $('#eval').val('').attr('data-index', -1).attr('rows', 1).css color: 'black'

    if current_frame.file == '<w>'
        file_cache[current_frame.file] = current_frame.f_code

    if current_frame.file != $('#sourcecode').attr('title')
        $('#sourcecode').html(file_cache[current_frame.file])
        $('#sourcecode').attr('title', current_frame.file)
    $('#sourcecode li.highlighted').removeClass('highlighted').addClass('highlighted-other')
    $('#sourcecode').animate((scrollTop: $('#sourcecode').find('li').eq(current_frame.lno - 1).addClass('highlighted').position().top - $('#sourcecode').innerHeight() / 2 + $('#sourcecode').scrollTop()), 1000)


code = (code, classes=[]) ->
    code = $('<code class="language">' + code + '</code>')
    for cls in classes
        code.addClass(cls)
    code


execute = (snippet) ->
    if snippet.indexOf('.') == 0
        switch snippet.substr(1)
            when 's' then ws.send('Step')
            when 'n' then ws.send('Next')
            when 'c' then ws.send('Continue')
            when 'q' then ws.send('Quit')
        return
    ws.send("Eval|#{snippet}")

print = (data) ->
    snippet = $('#eval').val()
    $('#scrollback').append nh = code(snippet, ['prompted'])
    nh.syntaxHighlight()
    $('#scrollback').append nh = code(data.result)
    nh.syntaxHighlight()
    # if data.exception
    #     a = $('<a>').attr('href', '/?__w__=__w__&what=sub_exception&which=' + data.exception)
    #     nh.wrap(a)

    $('#eval').val('').attr('data-index', -1).attr('rows', 1).css color: 'black'
    filename = $('.selected .tracefile').text()
    if not (filename of cmd_hist)
        cmd_hist[filename] = []
    cmd_hist[filename].unshift snippet
    persist()
    $('#interpreter').stop(true).animate((scrollTop: $('#scrollback').height()), 1000)

        # ((data) ->  # fail
        #     $('#eval').css color: 'red'
        #     setTimeout (-> 
        #         $('#eval').css color: 'black'), 1000
        # )

echo = (data) ->
    $('#scrollback').append $('<span>').text(data.message)

register_eval = ->
    $('#eval').on 'keydown', (e) ->
        if e.ctrlKey
            if e.keyCode == 38
                ws.send('Return')
                return false
            if e.keyCode == 39
                ws.send('Next')
                return false
            if e.keyCode == 40
                ws.send('Step')
                return false
            
        if e.keyCode == 13
            $eval = $(@)
            if not e.shiftKey
                execute $eval.val()
                false
            else
                $eval.attr('rows', parseInt($eval.attr('rows')) + 1)
            
        else if e.keyCode == 9
            $eval = $(@)
            txtarea = $eval.get(0)
            startPos = txtarea.selectionStart
            endPos = txtarea.selectionEnd
            if startPos or startPos == '0'
                $eval.val($eval.val().substring(0, startPos) + '    ' + $eval.val().substring(endPos, $eval.val().length))
            else
                $eval.val($eval.val() + '    ')
            false
        else if e.keyCode == 38  # Up
            $eval = $(@)
            filename = $('.selected .tracefile').text()
            if not e.shiftKey
                if filename of cmd_hist
                    index = parseInt($eval.attr('data-index')) + 1
                    if index >= 0 and index < cmd_hist[filename].length
                        to_set = cmd_hist[filename][index]
                        if index == 0
                            $eval.attr('data-current', $eval.val())
                        $eval.val(to_set)
                            .attr('data-index', index)
                            .attr('rows', to_set.split('\n').length)
                        false
        
        else if e.keyCode == 40  # Down
            $eval = $(@)
            filename = $('.selected .tracefile').text()
            if not e.shiftKey
                if filename of cmd_hist
                    index = parseInt($eval.attr('data-index')) - 1
                    if index >= -1 and index < cmd_hist[filename].length
                        if index == -1
                            to_set = $eval.attr('data-current')
                        else
                            to_set = cmd_hist[filename][index]
                        $eval.val(to_set)
                            .attr('data-index', index)
                            .attr('rows', to_set.split('\n').length)
                        false

    $('.traceline.current').click()
    $('#eval').focus()
