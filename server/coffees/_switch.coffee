class Switch extends Log
  constructor: (@wdb) ->
    super

    @$switch = $('.switch').click @switch.bind @

  switch: ->
    if @$switch.find('i').text().trim() is 'close'
      @wdb.disable()
    else
      parent.postMessage('activate', '*')
