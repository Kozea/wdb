class History extends Log
  constructor: (@prompt) ->
    super
    @index = -1
    @current = ''
    @currentPos = null

    try
      @history = JSON.parse(localStorage['history'] or '[]')
    catch e
      @fail e

  up: ->
    if @index is -1
      @current = @prompt.get()
      @currentPos = @prompt.code_mirror.getCursor()

    @index = Math.min(@history.length - 1, @index + 1)
    @sync()

  down: ->
    @index = Math.max(@index - 1, -1)
    @sync()

  sync: ->
    if @index is -1
      @prompt.set @current
      @prompt.code_mirror.setCursor @currentPos
    else
      @prompt.set @history[@index]
      @prompt.code_mirror.setCursor @prompt.code_mirror.lineCount(), 0

  historize: (snippet) ->
    return unless snippet
    while (index = @history.indexOf(snippet)) != -1
      @history.splice(index, 1)
    @history.unshift snippet
    localStorage and localStorage['history'] = JSON.stringify @history

  reset: ->
    @index = -1
    @current = ''
    @currentPos = null
