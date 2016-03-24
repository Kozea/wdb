class Traceback extends Log
  constructor: (@wdb) ->
    super
    @$traceback = $('.traceback')
    @$traceback.on 'click', '.trace-line', @select.bind @

  select: (e) ->
    level = $(e.currentTarget).attr('data-level')
    @wdb.select_trace level
    false

  make_trace: (trace) ->
    @clear()
    @show()
    for frame in trace
      $traceline = $('<a>',
        class:'trace-line ellipsis
        mdl-list__item mdl-list__item--three-line trace-' + frame.level)
        .attr('data-level', frame.level)
        .attr('title',
          "File \"#{frame.file}\", line #{frame.lno}, in #{frame.function}\n" +
          "    #{frame.code}")

      for brk in @wdb.cm.breakpoints[frame.file] or []
        unless brk.cond or brk.fun or brk.lno
          $traceline.addClass('breakpoint')
          break

      if frame.current
        $traceline.addClass('real-selected')

      $primary = $('<div>', class: 'mdl-list__item-primary-content')
      $primary.append $('<div>', class: 'ellipsis').text(frame.function)
      $primary
        .append($('<div>', class: 'mdl-list__item-text-body')
          .append $tracebody = $('<div>', class: 'ellipsis')
          .append $('<div>', class: 'ellipsis').text(
            frame.file.split('/').slice(-1)[0] + ':' + frame.lno))

      @wdb.code $tracebody, frame.code, ['ellipsis']

      $traceline.append $primary
      @$traceback.prepend $traceline

  hide: ->
    @$traceback.addClass('hidden')

  show: ->
    @$traceback.removeClass('hidden')

  clear: ->
    @$traceback.empty()
