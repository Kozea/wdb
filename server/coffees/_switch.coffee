class Switch extends Log
  constructor: (@wdb) ->
    super
    @$trace = $('.trace')
    @$switches = $('.switch').click (e) => @switch $(e.currentTarget)
    @$source = $('.source')
    @$interpreter = $('.interpreter')

  switch: ($switch)->
    if $switch.is('.power')
      if $switch.is('.off')
        @wdb.disable()
      else if $switch.is('.on')
        parent.postMessage('activate', '*')
    else if $switch.is('.code')
      if $switch.is('.off')
        @open_code()
      else if $switch.is('.on')
        @close_code()
    else if $switch.is('.term')
      if $switch.is('.off')
        @open_term()
      else if $switch.is('.on')
        @close_term()

  open_trace: ->
    @$trace.addClass('mdl-layout--fixed-drawer')

  close_trace: ->
    @$trace.removeClass('mdl-layout--fixed-drawer')

  open_code: ->
    @$switches.filter('.code').removeClass('off').addClass('on')
      .removeClass('mdl-button--accent')
    @$source.removeClass('hidden')
    @wdb.cm.size()

  close_code: ->
    @$switches.filter('.code').removeClass('on').addClass('off')
      .addClass('mdl-button--accent')
    @$source.addClass('hidden')
    @wdb.cm.size()

  open_term: ->
    @$switches.filter('.term').removeClass('off').addClass('on')
      .removeClass('mdl-button--accent')
    @$interpreter.removeClass('hidden')
    @wdb.cm.size()

  close_term: ->
    @$switches.filter('.term').removeClass('on').addClass('off')
      .addClass('mdl-button--accent')
    @$interpreter.addClass('hidden')
    @wdb.cm.size()
