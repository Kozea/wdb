file_cache = {}

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

get = (data, done, fail) ->
    if not @ajaws
        data.__w__ = '__w__'
        rq = $.ajax('/',
            dataType: 'json',
            data: data
        )
        if done
            rq.done done
        if fail
            rq.fail fail
    else
        ws.send('GET|' + JSON.stringify(data))
        @_done = done

code = (code, classes=[]) ->
    code = $('<code class="language">' + code + '</code>')
    for cls in classes
        code.addClass(cls)
    code

select = (frame) ->
    select_frame = (frame) ->
        $('.traceline').removeClass('selected')
        $('#trace-' + frame.level).addClass('selected')
        $('#eval').val('').attr('data-index', -1).attr('rows', 1).css color: 'black'
        
    scrollTo = (lno) ->
        $('#sourcecode li.highlighted').removeClass('highlighted').addClass('highlighted-other')
        $('#sourcecode').animate((scrollTop: $('#sourcecode').find('li').eq(lno - 1).addClass('highlighted').position().top - $('#sourcecode').innerHeight() / 2 + $('#sourcecode').scrollTop()), 1000)
        

    if frame.file == '<w>'
        file_cache[__w.id][frame.file] = 'lol'

    if frame.file == $('#sourcecode').attr('title')
        select_frame frame
        scrollTo frame.lno
        
    else if file_cache[__w.id][frame.file]
        select_frame frame
        $('#sourcecode').html(file_cache[__w.id][frame.file])
        $('#sourcecode').attr('title', frame.file)
        scrollTo frame.lno
    else
        get((
            what: 'file',
            which: frame.file),
            ((data) ->
                select_frame frame
                $('#sourcecode').empty().append nh = code(data.file, ['linenums'])
                nh.syntaxHighlight()
                $('#sourcecode').attr('title', frame.file)
                scrollTo frame.lno
                file_cache[__w.id][frame.file] = $('#sourcecode').html()
            )
        )

execute = (snippet, id, frame_level) ->
    if snippet.indexOf('.') == 0
        switch snippet.substr(1)
            when 's' then @ws.send('STEP')
            when 'c' then @ws.send('CONTINUE')
            when 'q' then @ws.send('QUIT')
        return
    get((
        what: 'eval',
        who: snippet,
        whose: id,
        where: frame_level),
        ((data) ->  # done
            $('#scrollback').append nh = code(snippet, ['prompted'])
            nh.syntaxHighlight()
            $('#scrollback').append nh = code(data.result)
            nh.syntaxHighlight()
            if data.exception
                a = $('<a>').attr('href', '/?__w__=__w__&what=sub_exception&which=' + data.exception)
                nh.wrap(a)
            
            $('#eval').val('').attr('data-index', -1).attr('rows', 1).css color: 'black'
            file = $('.selected .tracefile').text()
            if not (file of cmd_hist)
                cmd_hist[file] = []
            cmd_hist[file].unshift snippet
            persist()
            $('#interpreter').stop(true).animate((scrollTop: $('#scrollback').height()), 1000)
        ),
        ((data) ->  # fail
            $('#eval').css color: 'red'
            setTimeout (-> 
                $('#eval').css color: 'black'), 1000
        )
    )


@w_load = ->
    $('body').append($('<h1>').text(__w.type).append($('<small>').text(__w.value)))
    file_cache[__w.id] = {}
    $scrollback = $('<div>').attr('id', 'scrollback')
    
    $eval = $('<textarea>').attr(rows: 1, 'data-index': -1, id: 'eval')
    
    $prompt = $('<div>').attr('id', 'prompt')
    $prompt.append($eval)
    
    $interpreter = $('<div>').attr('id', 'interpreter')
    $interpreter.append($scrollback)
    $interpreter.append($prompt)
    
    $sourcecode = $('<div>').attr('id', 'sourcecode')

    $source = $('<div>').attr('id', 'source')
    $source.append($sourcecode)
    $source.append($interpreter)
    $('body').append($source)
    $traceback = $('<div>').attr('id', 'traceback')
    $('body').append($traceback)
    $source.css(height: $(window).height() - $('h1').outerHeight(true))
    $traceback.css(height: $(window).height() - $('h1').outerHeight(true))

    for frame in __w.frames
        $traceline = $('<div>')
            .addClass('traceline')
            .attr('id', 'trace-' + frame.level)
            .attr('data-level', frame.level)
        if frame.current
            $traceline.addClass('current')

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
        $traceback.prepend $traceline

    $('.traceline').each(->
        $(@).find('code').syntaxHighlight()
    ).on('click', ->
        select __w.frames[$(@).attr('data-level')] 
    )

    $('#eval').on 'keydown', (e) ->
        if e.keyCode == 13
            $eval = $(@)
            if not e.shiftKey
                execute $eval.val(), __w.id, $('.selected').attr('data-level')
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
            file = $('.selected .tracefile').text()
            if not e.shiftKey
                if file of cmd_hist
                    index = parseInt($eval.attr('data-index')) + 1
                    if index >= 0 and index < cmd_hist[file].length
                        to_set = cmd_hist[file][index]
                        if index == 0
                            $eval.attr('data-current', $eval.val())
                        $eval.val(to_set)
                            .attr('data-index', index)
                            .attr('rows', to_set.split('\n').length)
                        false
        
        else if e.keyCode == 40  # Down
            $eval = $(@)
            file = $('.selected .tracefile').text()
            if not e.shiftKey
                if file of cmd_hist
                    index = parseInt($eval.attr('data-index')) - 1
                    if index >= -1 and index < cmd_hist[file].length
                        if index == -1
                            to_set = $eval.attr('data-current')
                        else
                            to_set = cmd_hist[file][index]
                        $eval.val(to_set)
                            .attr('data-index', index)
                            .attr('rows', to_set.split('\n').length)
                        false

    $('.traceline.current').click()
    $('#eval').focus()
        
