class Interpreter extends Log
  constructor: (@wdb) ->
    super
    @$terminal = $('.terminal')
      .on 'click', @focus.bind @
      .on 'click', 'a.inspect', @inspect.bind @
    @$scrollback = $('.scrollback')
      .on 'click', '.short.close', @short_open.bind @
      .on 'click', '.short.open', @short_close.bind @
      .on 'click', '.toggle', @toggle_visibility.bind @


  scroll: (direction=null)->
    if direction
      @$terminal.scrollTop(
        @$terminal.scrollTop() + direction * @$terminal.height())
      return

    @wdb.prompt.$container.get(0).scrollIntoView
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

  focus: (e) ->
    scroll = @$terminal.scrollTop()
    @wdb.prompt.focus()
    @$terminal.scrollTop scroll
