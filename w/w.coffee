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
SyntaxHighlighter.defaults.quick-code = false;

$ ->
    $('body').append($('<h1>').text(__w.type).append($('<small>').text(__w.value)))
    traceback = $('<div>').attr('id', 'traceback')
    $('body').append(traceback)
    source = $('<div>').attr('id', 'source')
    $('body').append(source)

    get_file = (file, lno) ->
        -> $.ajax('',
        dataType: 'json',
        data:
            __w__: '__w__',
            what: 'file',
            which: file
        ).success((data) ->
            pre = $ '<pre>'
            source.empty().append pre
            pre.html data.file
            setTimeout (->
                SyntaxHighlighter.highlight((brush: 'python', highlight: [lno]), pre.get(0))
                source.scrollTop($('.line.number' + lno).position().top - 200)
            ), 100)
            
    get_eval = (code, id, frame_level, $traceline) ->
        $.ajax('',
            dataType: 'json',
            data:
                __w__: '__w__',
                what: 'eval',
                who: code,
                whose: id,
                where: frame_level
            ).success((data) ->
                pre = $('<pre>').text(' ' + data.result).attr('title', '>>> ' + code.replace(/\n/g, '<br>    ').replace(/\s/g, '&nbsp'))
                $traceline.find('.eval-results').append pre
                $traceline.find('.eval').val('').attr('data-index', -1).attr('rows', 1).css color: 'black'
                file = $traceline.find('.tracefile').text()
                if not (file of cmd_hist)
                    cmd_hist[file] = []
                cmd_hist[file].unshift code
                persist()
                SyntaxHighlighter.highlight (brush: 'python', gutter: false), pre.get(0)
            ).fail((data) ->
                $traceline.find('.eval').css color: 'red'
                setTimeout (-> 
                    $traceline.find('.eval').css color: 'black'), 1000
            )


    for frame in __w.frames
        traceline = $('<div>').addClass('traceline').attr('id', 'trace-' + frame.level).attr('data-level', frame.level)
        traceinfo = $('<div>').addClass('traceinfo')
        traceinfo
            .append($('<span>').addClass('tracetxt').text('File:  '))
            .append($('<span>').addClass('tracefile').text(frame.file).on('click', get_file(frame.file, frame.lno)))
            .append($('<span>').addClass('tracetxt').text(': '))
            .append($('<span>').addClass('tracelno').text(frame.lno))
            .append($('<span>').addClass('tracetxt').text(' in '))
            .append($('<span>').addClass('tracefun').text(frame.function))
            
        tracecode = $('<div>').addClass('tracecode')
        tracecode
            .append($('<pre>').addClass('code').text(frame.code))
        traceeval = $('<div>').addClass('traceeval')
        traceeval
            .append($('<div>').addClass('eval-results'))
            .append($('<div>').addClass('eval-prompt')
                .append($('<textarea>').attr('rows', 1).attr('data-index', -1).addClass('eval')))

        traceline.append traceinfo
        traceline.append tracecode
        traceline.append traceeval
        traceback.append traceline

    $('.traceline').each(->
        SyntaxHighlighter.highlight (brush: 'python', gutter: false), $(@).find('.tracecode .code').get(0)
    )

    $('.eval').on 'keydown', (e) ->
        if e.keyCode == 13
            $eval = $(@)
            if not e.shiftKey
                $traceline = $eval.closest '.traceline'
                get_eval $eval.val(), __w.id, $traceline.attr('data-level'), $traceline
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
            $traceline = $eval.closest '.traceline'
            file = $traceline.find('.tracefile').text()
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
            $traceline = $eval.closest '.traceline'
            file = $traceline.find('.tracefile').text()
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

    $('.tracefile').last().click()
    $('.eval').last().focus()
        
