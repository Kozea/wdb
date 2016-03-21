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
      lineWrapping: true
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
      'Ctrl-C': @abort.bind @
      'Ctrl-D': =>
        unless @get()
          @wdb.die()
      'Ctrl-F': ->
      'Ctrl-R': @searchBack.bind @
      'Ctrl-Enter': 'newlineAndIndent'
      'Alt-Backspace': 'delGroupBefore'
      'Ctrl-Space': (cm, options) ->
        CodeMirror.commands.autocomplete cm, CodeMirror.hint.jedi,
          async: true
          extraKeys:
            Right: (cm, handle) -> handle.pick()
      # Use page up/down for going up/down in multiline
      'PageUp': 'goLineUp'
      'PageDown': 'goLineDown'

    @code_mirror.on 'keyup', (cm, e) =>
      return unless cm.getValue()
      return if 8 < e.keyCode < 42
      CodeMirror.commands.autocomplete cm, CodeMirror.hint.jedi,
        async: true
        completeSingle: false
        # If auto hint restore these defaults
        extraKeys:
          PageUp: 'goPageUp'
          PageDown: 'goPageDown'
          Home: 'goLineStartSmart'
          Up: (cm, handle) ->
            handle._dirty = true
            handle.moveFocus(-1)
          Down: (cm, handle) ->
            handle._dirty = true
            handle.moveFocus(1)
          Enter: (cm, handle) =>
            if handle._dirty
              handle.pick()
            else
              @newLineOrExecute cm
          Right:
            (cm, handle) ->
              if handle._dirty
                handle.pick()
              else
                CodeMirror.commands.goCharRight cm
          End: 'goLineEnd'

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
    return unless snippet
    cm.setOption 'readOnly', true
    @$container.addClass 'loading'
    @wdb.execute snippet

  focus: ->
    @code_mirror.focus()

  abort: ->
    @history.reset()
    @set ''

  ready: (suggest=null, newline=false)->
    if newline
      @code_mirror.execCommand 'newlineAndIndent'
    else
      snippet = @code_mirror.getValue().trim()
      @history.historize snippet
      @history.reset()
      @set suggest or ''
    @$container.removeClass 'loading'
    @code_mirror.setOption 'readOnly', false
    @focus()

  get: ->
    @code_mirror.getValue()

  set: (val) ->
    @code_mirror.setValue(val)

  searchBack: ->
    @$code_mirror.addClass 'extra-dialog'
    close = @code_mirror.openDialog(
      '''
        Search:
        <input type="text" style="width: 10em" class="CodeMirror-search-field"/>
      '''
      , (val, e) =>
        console.log('commit')
        @history.commitSearch()
      ,
        bottom: true
        onInput: (e, val, close) =>
          return unless val
          @history.resetSearch()
          @history.searchNext val
        onKeyDown: (e, val, close) =>
          if e.keyCode is 82
            if e.ctrlKey
              val and @history.searchNext val
            if e.altKey
              val and @history.searchPrev val
            if e.ctrlKey or e.altKey
              e.preventDefault()
              e.stopPropagation()
          return false

        onClose: (dialog) =>
          @history.rollbackSearch()
          @$code_mirror.removeClass 'extra-dialog'
    )
