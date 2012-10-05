$ ->
    for [file, lno, func, code] in _
        $('body')
            .append($('<em>').text(file))
            .append($('<span>').text(': '))
            .append($('<mark>').text(lno))
            .append($('<span>').text('in'))
            .append($('<strong>').text(func))
            .append($('<pre>').text(code))
            .append('<br>')
