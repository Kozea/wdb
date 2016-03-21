class Interpreter extends Log
  constructor: (@wdb) ->
    super
    @$interpreter = $('.interpreter')
      .on 'click', @focus.bind @
    @$scrollback = $('.scrollback')
      .on 'click', 'a.inspect', @inspect.bind @
      .on 'click', '.short.close', @short_open.bind @
      .on 'click', '.short.open', @short_close.bind @
      .on 'click', '.toggle', @toggle_visibility.bind @


  scroll: ->
    @$interpreter.get(0).scrollIntoView
      block: "end"
      behavior: "smooth"

  clear: ->
    @$scrollback.empty()

  write: (elt) ->
    @$scrollback.append elt

  inspect: (e) ->
    @wdb.inspect $(e.currentTarget).attr('href')

  short_open: (e) ->
    $(e.currentTarget)
      .addClass('open')
      .removeClass('close')
      .next('.long')
      .show('fast')

  short_close: (e) ->
    $(e.currentTarget)
      .addClass('close')
      .removeClass('open')
      .next('.long')
      .hide('fast')

  toggle_visibility: (e) ->
    $(e.currentTarget)
      .add($(e.currentTarget).next())
      .toggleClass('closed', 'shown')

  focus: ->
    scroll = @$interpreter.scrollTop()
    @wdb.prompt.focus()
    @$interpreter.scrollTop scroll
