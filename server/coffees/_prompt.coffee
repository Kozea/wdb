class Prompt extends Log
  constructor: (@wdb) ->
    super
    @$container = $('.prompt')

    @code_mirror = CodeMirror (elt) =>
      @$code_mirror = $ elt
      @$container.prepend(elt)
    ,
      value: '',
      theme: 'default',
      language: 'python'
      viewportMargin: Infinity

    CodeMirror.registerHelper "hint", "jedi",
      (cm, callback, options) =>
        cur = cm.getCursor()
        tok = cm.getTokenAt(cur)

        @wdb.ws.send 'Complete',
          source: cm.getValue()
          pos: @code_mirror.getRange({line: 0, ch: 0}, cur).length
          line: cur.line + 1
          column: cur.ch

        @completion =
          from: CodeMirror.Pos(cur.line, tok.start)
          to: CodeMirror.Pos(cur.line, tok.end)
          callback: callback

    @code_mirror.addKeyMap
      'Enter': (cm) => @wdb.execute(@code_mirror.getValue())
      'Ctrl-Enter': 'newlineAndIndent'
      'Ctrl-Space': (cm, options) ->
        CodeMirror.commands.autocomplete(cm, CodeMirror.hint.jedi, async: true)

  complete: (data) ->
    return unless @completion
    @completion.callback
      from: @completion.from
      to: @completion.to
      list: (
        text: completion.base + completion.complete
        _completion: completion
        render: (elt, data, cur) ->
          c = cur._completion
          item = "<b>#{c.base}</b>#{c.complete}"
          $(elt).html item
      ) for completion in data.completions
