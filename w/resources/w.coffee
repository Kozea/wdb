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

SyntaxHighlighter.defaults.toolbar = false;
SyntaxHighlighter.defaults['quick-code'] = false;

select = (frame) ->
    select_frame = (frame) ->
        $('.traceline').removeClass('selected')
        $('#trace-' + frame.level).addClass('selected')
        $('#eval').val('').attr('data-index', -1).attr('rows', 1).css color: 'black'
        
    if file_cache[__w.id][frame.level]
        select_frame frame
        $('#sourcecode').html(file_cache[__w.id][frame.level])
        $('#sourcecode').scrollTop($('.line.number' + frame.lno).position().top - $('#sourcecode').innerHeight() / 2)
    else
        $.ajax('/',
            dataType: 'json',
            data:
                __w__: '__w__',
                what: 'file',
                which: frame.file
        ).done((data) ->
            select_frame frame
            pre = $ '<pre>'
            $('#sourcecode').empty().append pre
            pre.html data.file
            setTimeout (->
                SyntaxHighlighter.highlight((brush: 'python', highlight: [frame.lno]), pre.get(0))
                $('#sourcecode').scrollTop($('.line.number' + frame.lno).position().top - $('#sourcecode').innerHeight() / 2)
                file_cache[__w.id][frame.level] = $('#sourcecode').html()
            ), 100
        )

execute = (code, id, frame_level) ->
    $.ajax('/',
        dataType: 'json',
        data:
            __w__: '__w__',
            what: 'eval',
            who: code,
            whose: id,
            where: frame_level
        ).done((data) ->
            pre = $('<pre>').text(' ' + data.result).attr('title', '>>> ' + code.replace(/\n/g, '<br>    ').replace(/\s/g, '&nbsp'))
            if data.exception
                a = $('<a>').attr('href', '/?__w__=__w__&what=sub_exception&which=' + data.exception).append(pre)
            $('#scrollback').prepend a or pre
            $('#eval').val('').attr('data-index', -1).attr('rows', 1).css color: 'black'
            file = $('.selected .tracefile').text()
            if not (file of cmd_hist)
                cmd_hist[file] = []
            cmd_hist[file].unshift code
            persist()
            SyntaxHighlighter.highlight (brush: 'python', gutter: false), pre.get(0)

        ).fail((data) ->
            $('#eval').css color: 'red'
            setTimeout (-> 
                $('#eval').css color: 'black'), 1000
        )


$ ->
    $('body').append($('<h1>').text(__w.type).append($('<small>').text(__w.value)))
    file_cache[__w.id] = {}
    $scrollback = $('<div>').attr('id', 'scrollback')
    
    $eval = $('<textarea>').attr(rows: 1, 'data-index': -1, id: 'eval')
    
    $prompt = $('<div>').attr('id', 'prompt')
    $prompt.append($eval)
    
    $interpreter = $('<div>').attr('id', 'interpreter')
    $interpreter.append($prompt)
    $interpreter.append($scrollback)
    
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
            
        $traceinfo = $('<div>')
            .addClass('traceinfo')
            .append($('<span>').addClass('tracefile').text(frame.file))
            .append($('<span>').addClass('tracetxt').text(': '))
            .append($('<span>').addClass('tracelno').text(frame.lno))
            .append($('<span>').addClass('tracetxt').text(' in '))
            .append($('<span>').addClass('tracefun').text(frame.function))
            
        $tracecode = $('<div>')
            .addClass('tracecode')
            .append($('<pre>').addClass('code').text(frame.code))

        $traceline.append $traceinfo
        $traceline.append $tracecode
        $traceback.prepend $traceline

    $('.traceline').each(->
        SyntaxHighlighter.highlight (brush: 'python', gutter: false), $(@).find('.tracecode .code').get(0)
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

    $('.traceline').first().click()
    $('#eval').focus()
        
