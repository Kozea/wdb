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
        class:'trace-line
        mdl-list__item mdl-list__item--two-line trace-' + frame.level)
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

      $primary = $('<span>', class: 'mdl-list__item-primary-content')
        .text(frame.function)

      $primary.append($('<span>', class: 'mdl-list__item-sub-title')
        .text(frame.file.split('/').slice(-1)[0] + ':' + frame.lno))

      $secondary = $('<span>', class: 'mdl-list__item-secondary-content')
      @wdb.code $secondary, frame.code

      # $tracefilelno = $('<span>')
      #   .addClass('mdl-list__item-primary-content')
      #   .append $('<span>', title: frame.file).text()
      #
      #   .append $('<span>', title: frame.file).text()
      #   .append($tracefile = $('<span>', title: frame.file)
      #     .addClass('trace-file')
      #     .append $('<sup>').addClass('trace-lno').text(frame.lno)
      #     .text(frame.filename))
      #   .append $('<span>').addClass('trace-fun').text(frame.function)

      # $tracecode = $('<span>')
      #   .addClass('tracecode')
      #
      # @code $tracecode, frame.code

      $traceline
        .append $primary
        .append $secondary
      @$traceback.prepend $traceline

  hide: ->
    @$traceback.addClass('hidden')

  show: ->
    @$traceback.removeClass('hidden')

  clear: ->
    @$traceback.empty()
