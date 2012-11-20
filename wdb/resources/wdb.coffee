# This file is part of wdb
#
# wdb Copyright (C) 2012  Florian Mounier, Kozea
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

#### Initializations ####
time = ->
    d = new Date()
    "#{d.getHours()}:#{d.getMinutes()}:#{d.getSeconds()}.#{d.getMilliseconds()}"

started = false
stop = false
ws = null

send = (msg) ->
    console.log time(), '->', msg
    ws.send msg

persistable = 'localStorage' of window and window.localStorage
if persistable and localStorage['__wdb_cmd_hist']
    try
        cmd_hist = JSON.parse localStorage['__wdb_cmd_hist']
        file_cache = JSON.parse localStorage['__wdb_file_cache']
    catch e
        file_cache = {}
        cmd_hist = {}
else
    file_cache = {}
    cmd_hist = {}

persist = ->
    if not persistable
        return
    localStorage['__wdb_cmd_hist'] = JSON.stringify cmd_hist
    localStorage['__wdb_file_cache'] = JSON.stringify file_cache

$.SyntaxHighlighter.loadedExtras = true
$.SyntaxHighlighter.init(
    debug: true,
    lineNumbers: false,
    highlight: false,
    load: false)
    
make_ws = ->
    # Open a websocket in case of request break
    console.log 'Opening new socket'
    new_ws = new WebSocket "ws://" + document.location.hostname + ":" + @__ws_port
    new_ws.onclose = (m) =>
        console.log "close #{m}"
        if not stop
            setTimeout (=>
                @ws = ws = make_ws()), 1000

    new_ws.onerror = (m) =>
        console.log "WebSocket error", m
        if not stop
            setTimeout (=>
                @ws = ws = make_ws()), 1000
            
    new_ws.onopen = (m) ->
        # We are connected, ie: in request break
        console.log "WebSocket is open", m
        # Start by getting current trace
        if not started
            register_handlers()
            started = true
        send('Start')
        $('body').show()
        $('#eval').focus()

    new_ws.onmessage = (m) ->
        if stop
            return
        # Open a websocket in case of request break
        pipe = m.data.indexOf('|')
        if pipe > -1
            cmd = m.data.substr(0, pipe)
            data = JSON.parse m.data.substr(pipe + 1)
        else
            cmd = m.data
        console.log time(), '<-', cmd
        switch cmd
            when 'Title'  then title  data
            when 'Trace'  then trace  data
            when 'File'   then file   data
            when 'Check'  then check  data
            when 'Select' then select data
            when 'Print'  then print  data
            when 'Echo'   then echo   data
            when 'Dump'   then echo   data
    new_ws

#### Loading ####
$ =>
    # Try getting the original page
    end = (page) ->
        stop = true
        if ws
            try
                send('Quit')
                ws.close()
            catch e
                {}
        document.open()
        document.write page
        document.close()

    if __ws_post
        xhr = $.ajax(location.href,
            type: 'POST',
            data: __ws_post.data,
            contentType: __ws_post.enctype,
            traditional: true)
    else
        xhr = $.ajax(location.href)

    xhr.done((data) => end(data))
       .fail (data) =>
            if data.responseText
                end(data.responseText)

    @ws = ws = make_ws()

    @onbeforeunload = ->
        try
            console.log('Try jit quit')
            send('Quit')
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
        code($tracecode, frame.code)
        $traceline.append $tracefilelno
        $traceline.append $tracecode
        $traceline.append $tracefunfun
        $('#traceback').prepend $traceline
    # $('.traceline').each(->
        # $(@).find('code').syntaxHighlight()
    # )
    $('.traceline').on('click', ->
        send('Select|' + $(@).attr('data-level'))
    )
        

file = (data) ->
    code($('#sourcecode').empty(), data.file, ['linenums'])
    $('#sourcecode').attr('title', data.name)
    file_cache[data.name] = file: $('#sourcecode').html(), sha512: data.sha512
    persist()

check = (data) ->
    filename = data.name
    if filename not of file_cache or file_cache[filename].sha512 != data.sha512
        send("File")
    else
        send("NoFile")
    $('#eval').asuggest(data.words)

select = (data) ->
    current_frame = data.frame
    $('.traceline').removeClass('selected')
    $('#trace-' + current_frame.level).addClass('selected')
    $('#eval').val('').attr('data-index', -1).attr('rows', 1).css color: 'black'

    # if current_frame.file == '<wdb>'
        # file_cache[current_frame.file] = current_frame.f_code

    if current_frame.file != $('#sourcecode').attr('title')
        $('#sourcecode').html(file_cache[current_frame.file].file)
        $('#sourcecode').attr('title', current_frame.file)
    $('#sourcecode li.highlighted').removeClass('highlighted').addClass('highlighted-other')
    $('#sourcecode').stop().animate((scrollTop: $('#sourcecode').find('li').eq(current_frame.lno - 1).addClass('highlighted').position().top - $('#sourcecode').innerHeight() / 2 + $('#sourcecode').scrollTop()), 100)


code = (parent, code, classes=[]) ->
    code = $('<code class="language">' + code + '</code>')
    for cls in classes
        code.addClass(cls)
    parent.append code
    code.syntaxHighlight()
    code.find('span').each ->
        txt = $(@).text()
        if txt.length > 128
            $(@).text ''
            $(@).append $('<span class="short close">').text(txt.substr(0, 128))
            $(@).append $('<span class="long">').text(txt.substr(128))
    code

last_cmd = null
execute = (snippet) ->
    cmd = (cmd) ->
            send cmd
            last_cmd = cmd

    if snippet.indexOf('.') == 0
        space = snippet.indexOf(' ')
        if space > -1
            key = snippet.substr(1, space - 1)
            data = snippet.substr(space + 1)
        else
            key = snippet.substr(1)
            data = ''
        switch key
            when 's' then cmd('Step')
            when 'n' then cmd('Next')
            when 'r' then cmd('Return')
            when 'c' then cmd('Continue')
            when 'q' then cmd('Quit')
            when 'p' then cmd('Eval|pprint(' + data + ')')
        return
    else if snippet == '' and last_cmd
        cmd last_cmd
        return
    send("Eval|#{snippet}")

print = (data) ->
    snippet = $('#eval').val()
    code($('#scrollback'), snippet, ['prompted'])
    code($('#scrollback'), data.result)

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
    code($('#scrollback'), data.for, ['prompted'])
    code($('#scrollback'), data.val or '')
    $('#interpreter').stop(true).animate((scrollTop: $('#scrollback').height()), 1000)
        

register_handlers = ->
    $('body,html').on 'keydown', (e) ->
        if e.ctrlKey
            if e.keyCode == 37  # left
                send('Continue')
                return false
            if e.keyCode == 38  # up
                send('Return')
                return false
            if e.keyCode == 39  # Right
                send('Next')
                return false
            if e.keyCode == 40  # Down
                send('Step')
                return false

    $('#eval').on 'keydown', (e) ->
        if e.ctrlKey
            e.stopPropagation()
            return
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

    $("#scrollback").on('click', 'a.inspect', ->
        ws.send('Inspect|' + $(this).attr('href'))
        false
    ).on('click', '.short.close', ->
        $(@).addClass('open').removeClass('close').next('.long').show('fast')
    ).on 'click', '.long,.short.open', ->
        elt = if $(@).hasClass('long') then $(@) else $(@).next('.long')
        elt.hide('fast').prev('.short').removeClass('open').addClass('close')
