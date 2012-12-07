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
__ws_port = 10000 + parseInt(Math.random() * 50000)
cmd_hist = {}

$sourcecode = null
$traceback = null

send = (msg) ->
    console.log time(), '->', msg
    ws.send msg

@indexedDB = @indexedDB or @mozIndexedDB or @webkitIndexedDB or @msIndexedDB
@IDBTransaction = @IDBTransaction or @webkitIDBTransaction or @msIDBTransaction
@IDBKeyRange = @IDBKeyRange or @webkitIDBKeyRange or @msIDBKeyRange

fallback = ->
    file_cache = {}
    @get = (type) -> (obj, callback) -> callback(obj of file_cache and file_cache[obj])
    @set = (type) -> (obj) -> file_cache[obj.name] = obj

if not @indexedDB
    fallback()
else
    open = @indexedDB.open('wdbdb', 2)
    open.onerror = (event) -> console.log('Error when opening wdbdb', event)
    open.onupgradeneeded = (event) ->
        db = event.target.result
        db.createObjectStore("file", { keyPath: "name" })
        db.createObjectStore("cmd", { keyPath: "name" })

    open.onsuccess = (event) =>
        console.info 'wdbdb is open'
        @wdbdb = open.result
        @get = (type) ->
            (key, callback, notfound, always) ->
                rq = @wdbdb.transaction([type]).objectStore(type).get(key)
                rq.onsuccess = (event) ->
                    if event.target.result
                        callback(event.target.result)
                    else
                        notfound and notfound()
                    always and always()
                if notfound
                    rq.onerror = (event) ->
                        notfound()
                        always and always()
                null
        @set = (type) ->
            (obj) ->
                rq = @wdbdb.transaction([type], 'readwrite')
                os = rq.objectStore(type)
                os.put(obj)
                rq.oncomplete = (event) -> console.log('Set')
                rq.onerror = (event) -> console.log('Add error', event)
                null

        @wdbdb.transaction(['cmd']).objectStore('cmd').openCursor().onsuccess = (event) ->
            cursor = event.target.result
            if cursor
                cmd_hist[cursor.value.name] = cursor.value.history
                cursor.continue()

    open.onerror = (event) ->
        console.log('Error when opening wdbdb', event)
        fallback()    

$.SyntaxHighlighter.loadedExtras = true
$.SyntaxHighlighter.init(
    debug: true,
    lineNumbers: false,
    highlight: false,
    load: false)
    
make_ws = ->
    # Open a websocket in case of request break
    console.log 'Opening new socket'
    new_ws = new WebSocket "ws://" + document.location.hostname + ":" + __ws_port
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
        start()

        $('body').show()
        $('#eval').focus()

    new_ws.onmessage = (m) ->
        if stop
            return
        # Open a websocket in case of request break
        message = m.data
        pipe = message.indexOf('|')
        if pipe > -1
            cmd = message.substr(0, pipe)
            data = JSON.parse message.substr(pipe + 1)
        else
            cmd = message
        console.log time(), '<-', cmd
        switch cmd
            when 'Title'      then title      data
            when 'Trace'      then trace      data
            when 'File'       then file       data
            when 'Check'      then check      data
            when 'Select'     then select     data
            when 'Print'      then print      data
            when 'Echo'       then echo       data
            when 'BreakSet'   then breakset   data
            when 'BreakUnset' then breakunset data
            when 'Dump'       then echo       data
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
            traditional: true,
            headers: 'X-Debugger': 'WDB-' + __ws_port)
    else
        xhr = $.ajax(location.href,
            headers: 'X-Debugger': 'WDB-' + __ws_port)

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

start = ->
    send('Start')
    $sourcecode = $('#sourcecode')
    $traceback = $('#traceback')

title = (data) ->
    $('#title').text(data.title).append($('<small>').text(data.subtitle))
    $('#source').css(height: $(window).height() - $('#title').outerHeight(true))
    $traceback.css(height: $(window).height() - $('#title').outerHeight(true))

trace = (data) ->
    $traceback.empty()
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

        $tracecode = $('<div>').addClass('tracecode')
        code($tracecode, frame.code)
        $traceline.append $tracefilelno
        $traceline.append $tracecode
        $traceline.append $tracefunfun
        $traceback.prepend $traceline
    # $('.traceline').each(->
        # $(@).find('code').syntaxHighlight()
    # )
    $('.traceline').on('click', ->
        send('Select|' + $(@).attr('data-level'))
    )


file = (data) ->
    code($sourcecode.empty(), data.file, ['linenums'])
    $sourcecode.attr('title', data.name)
    set('file')(name: data.name, file: $sourcecode.html(), sha512: data.sha512)

check = (data) =>
    @get('file')(data.name,
        ((file) ->
            if file.sha512 != data.sha512
                send('File')
            else    
                send('NoFile')
        ), (->
            send('File')))
    $('#eval').asuggest(data.words)

select = (data) ->
    current_frame = data.frame
    $('.traceline').removeClass('selected')
    $('#trace-' + current_frame.level).addClass('selected')
    $('#eval').val('').attr('data-index', -1).attr('rows', 1).css color: 'black'

    # if current_frame.file == '<wdb>'
        # file_cache[current_frame.file] = current_frame.f_code

    get('file')(current_frame.file,
        (file) ->
            $sourcecode.html(file.file)
            $sourcecode.attr('title', current_frame.file)
            $('#sourcecode li.highlighted').removeClass('highlighted').addClass('highlighted-other')
            for lno in data.breaks
                $('.linenums li').eq(lno - 1).addClass('breakpoint')
            $cur_line = $sourcecode.find('li').eq(current_frame.lno - 1)
            $cur_line.addClass('highlighted')

            $sourcecode.find('li.ctx').removeClass('ctx')
            for lno in [current_frame.flno...current_frame.llno + 1]
                $line = $sourcecode.find('li').eq(lno - 1)
                $line.addClass('ctx')
                if lno == current_frame.flno
                    $line.addClass('ctx-top')
                else if lno == current_frame.llno
                    $line.addClass('ctx-bottom')
            $sourcecode.stop().animate((scrollTop: $cur_line.position().top - $sourcecode.innerHeight() / 2 + $sourcecode.scrollTop()), 100)
        )



code = (parent, code, classes=[]) ->
    code = $('<code class="language">' + code + '</code>')
    for cls in classes
        code.addClass(cls)
    parent.append code
    code.syntaxHighlight()
    # Re do it in case of
    setTimeout((->
        code.syntaxHighlight()), 50)
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
            when 'u' then cmd('Until')
            when 'q' then cmd('Quit')
            when 'p' then cmd('Eval|pprint(' + data + ')')
            when 'j' then cmd('Jump|' + data)
            when 'b' then toggle_break(data)
            when 't' then toggle_break(data, true)
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
    #     a = $('<a>').attr('href', '/?__ws__=__ws__&what=sub_exception&which=' + data.exception)
    #     nh.wrap(a)

    $('#eval').val('').attr('data-index', -1).attr('rows', 1).css color: 'black'

    filename = $('.selected .tracefile').text()
    if not (filename of cmd_hist)
        cmd_hist[filename] = []
    cmd_hist[filename].unshift snippet

    set('cmd')(name: filename, history: cmd_hist[filename])
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

breakset = (data) ->
    $line = $('.linenums li').eq(data.lno - 1)
    $line.removeClass('ask-breakpoint').addClass('breakpoint')
    if data.cond
        $line.attr('title', "On [#{data.cond}]")
    $eval = $('#eval')
    if $eval.val().indexOf('.b ') == 0 or $eval.val().indexOf('.t ') == 0
        $eval.val('')

breakunset = (data) ->
    $('.linenums li').eq(data.lno - 1).removeClass('ask-breakpoint').attr('title', '')
    $eval = $('#eval')
    if $eval.val().indexOf('.b ') == 0
        $eval.val('')

toggle_break = (lno, temporary) ->
    cmd = if temporary then 'TBreak' else 'Break'
    if ('' + lno).indexOf(':') > -1
        send(cmd + '|' + lno)
    $line = $('.linenums li').eq(lno - 1)
    if $line.hasClass('breakpoint')
        send('Unbreak|' + lno)
        $line.removeClass('breakpoint').addClass('ask-breakpoint')
    else
        $line.addClass('ask-breakpoint')
        send(cmd + '|' + lno)
    
register_handlers = ->
    $('body,html').on 'keydown', (e) ->
        if (e.ctrlKey and e.keyCode == 37) or e.keyCode == 119 # ctrl + left  or F8
            send('Continue')
            return false
        if (e.ctrlKey and e.keyCode == 38) or e.keyCode == 120 # ctrl + up    or F9
            send('Return')
            return false
        if (e.ctrlKey and e.keyCode == 39) or e.keyCode == 121 # ctrl + right or F10
            send('Next')
            return false
        if (e.ctrlKey and e.keyCode == 40) or e.keyCode == 122 # ctrl + down  or F11
            send('Step')
            return false
        if e.keyCode == 118 # F7
            send('Until')
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
        send('Inspect|' + $(this).attr('href'))
        false
    ).on('click', '.short.close', ->
        $(@).addClass('open').removeClass('close').next('.long').show('fast')
    ).on('click', '.long,.short.open', ->
        elt = if $(@).hasClass('long') then $(@) else $(@).next('.long')
        elt.hide('fast').prev('.short').removeClass('open').addClass('close')
    )

    $("#sourcecode").on('click', '.linenums li', ->
        lno = $(@).parent().find('li').index(@) + 1
        toggle_break(lno)
    )
