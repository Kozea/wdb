class Prompt extends Log
  constructor: (@wdb) ->
    super
    @$container = $('.prompt')
    @history = new History @

    @code_mirror = CodeMirror (elt) =>
      @$code_mirror = $ elt
      @$container.prepend(elt)
    ,
      value: '',
      theme: 'default',
      language: 'python'
      viewportMargin: Infinity
      autofocus: true

    CodeMirror.registerHelper "hint", "jedi",
      (cm, callback, options) =>
        cur = cm.getCursor()
        tok = cm.getTokenAt(cur)
        unless options.completeSingle
          # Auto triggered
          return unless tok.string.match /[\w\.\(\[\{]/

        @wdb.ws.send 'Complete',
          source: cm.getValue()
          pos: @code_mirror.getRange({line: 0, ch: 0}, cur).length
          line: cur.line + 1
          column: cur.ch

        @completion =
          cur: cur
          tok: tok
          from: CodeMirror.Pos(cur.line, tok.start)
          to: CodeMirror.Pos(cur.line, tok.end)
          callback: callback

    @code_mirror.addKeyMap
      'Enter': @newLineOrExecute.bind @
      'Up': @history.up.bind @history
      'Down': @history.down.bind @history
      'Ctrl-Enter': 'newlineAndIndent'
      'Ctrl-Space': (cm, options) ->
        CodeMirror.commands.autocomplete(cm, CodeMirror.hint.jedi, async: true)

    @code_mirror.on 'keyup', (cm, e) ->
      return unless cm.getValue()
      return if e.keyCode in [37, 38, 39, 40, 13, 27]
      CodeMirror.commands.autocomplete cm, CodeMirror.hint.jedi,
        async: true
        completeSingle: false

  complete: (data) ->
    return unless @completion
    cur = @completion.cur
    tok = @completion.tok
    @completion.callback
      from: CodeMirror.Pos(cur.line, tok.start)
      to: CodeMirror.Pos(cur.line, tok.end)
      list: (
        text: completion.base + completion.complete
        from: CodeMirror.Pos(cur.line, cur.ch - completion.base.length)
        to: cur
        _completion: completion
        render: (elt, data, cur) ->
          c = cur._completion
          item = "<b>#{c.base}</b>#{c.complete}"
          $(elt).html item
      ) for completion in data.completions

  newLineOrExecute: (cm) ->
    snippet = cm.getValue().trim()
    @wdb.execute snippet
    cm.setOption readOnly: true

  newLine: ->
    @code_mirror.execCommand 'newlineAndIndent'

  newPrompt: ->
    snippet = @code_mirror.getValue().trim()
    # TODO: Hist
    @history.historize snippet
    @code_mirror.setValue ''
    cm.setOption readOnly: false

  focus: ->
    @code_mirror.focus()

  set: (val) ->
    @code_mirror.setValue(val)
