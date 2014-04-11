$ ->
  $('#activate').click () ->
    # Doesn't work in webkit for POSTS because of
    #  https://bugs.webkit.org/show_bug.cgi?id=23735 T_T
    $.get('/__wdb/on').done(() -> location.reload(true))
    false

  $('#title').text(_title).append($('<small>').text(_subtitle))
  if trace.trace
    $('#wdb').append($trace = $('<article>', class: 'trace_500'))

    for [file, lno, fun, code] in trace.trace
      $trace.append($('<div>', class: 'traceline').append(
        $('<div>', class: 'flno').text('File ' + file + ':' + lno),
        $('<div>', class: 'fun').text(fun),
        $code = $('<code>', class: 'cm')
      ))
      CodeMirror.runMode code or ' ', "python", $code.get(0)
