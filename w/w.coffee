SyntaxHighlighter.defaults['toolbar'] = false;
SyntaxHighlighter.defaults['quick-code'] = false;

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
                $traceline.find('.eval-results').append(pre = $('<pre>').text(' ' + data.result))
                $traceline.find('.eval').val('')
                console.log data.result
                SyntaxHighlighter.highlight((brush: 'python', gutter: false), pre.get(0))
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
            .append($('<input>').addClass('eval'))

        traceline.append traceinfo
        traceline.append tracecode
        traceline.append traceeval
        traceback.append traceline

    $('.traceline').each(->
        SyntaxHighlighter.highlight((brush: 'python', gutter: false), $(@).find('.tracecode .code').get(0))
    )

    $('.tracefile').last().click()
    $('.eval').on 'keydown', (e) ->
        if e.keyCode == 13
            $eval = $(@)
            $traceline = $eval.closest('.traceline')
            get_eval $eval.val(), __w.id, $traceline.attr('data-level'), $traceline
