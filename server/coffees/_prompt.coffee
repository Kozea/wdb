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
        from = CodeMirror.Pos(cur.line, tok.start)
        to = CodeMirror.Pos(cur.line, tok.end)
        if cm.getValue() is '.'
          callback
            from: from
            to: to
            list: (
              (text: '.' + key,
              displayText: ".#{key} <i>#{@leftpad('(' + help + ')', 14)}</i>  ",
              render: (elt, data, cur) ->
                $(elt).html cur.displayText
              ) for own key, help of {
                b: 'Break'
                c: 'Continue'
                d: 'Dump'
                e: 'Edition'
                f: 'Find'
                g: 'Clear'
                h: 'Help'
                i: 'Display'
                j: 'Jump'
                l: 'Breakpoints'
                n: 'Next'
                q: 'Quit'
                r: 'Return'
                s: 'Step'
                t: 'Tbreak'
                u: 'Until'
                w: 'Watch'
                x: 'Diff'
                z: 'Unbreak'
            })
          return

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
          from: from
          to: to
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
      'Ctrl-R': => @searchBack()
      'Ctrl-S': => @searchBack false
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

  leftpad: (str, n, c=' ') ->
    p = n - str.length
    for i in [0..p]
      str = c + str
    str

  searchBack: (back=true)->
    @$code_mirror.addClass 'extra-dialog'
    close = @code_mirror.openDialog(
      """
        <span class="search-dialog-title">
          Search #{if back then 'backward' else 'forward'}:
        </span>
        <input type="text" style="width: 10em" class="CodeMirror-search-field"/>
      """
      , (val, e) =>
        console.log('commit')
        @history.commitSearch()
      ,
        bottom: true
        onInput: (e, val, close) =>
          return unless val
          console.log('1', @history.index)
          @history.resetSearch()
          console.log('2', @history.index)
          $('.CodeMirror-search-field').toggleClass(
            'not-found',
            val and not
            @history[if close.back then 'searchNext' else 'searchPrev'](val))
          console.log('3', @history.index)
        onKeyDown: (e, val, close) =>
          console.log('4', @history.index)
          if e.keyCode is 82 and e.ctrlKey or e.keyCode is 83 and e.altKey
            close.back = true
            $('.search-dialog-title').text('Search backward:')
            $('.CodeMirror-search-field').toggleClass(
              'not-found', val and not @history.searchNext(val))
            e.preventDefault()
            e.stopPropagation()
          if e.keyCode is 83 and e.ctrlKey or e.keyCode is 82 and e.altKey
            close.back = false
            $('.search-dialog-title').text('Search forward:')
            $('.CodeMirror-search-field').toggleClass(
              'not-found', val and not @history.searchPrev(val))
            e.preventDefault()
            e.stopPropagation()
          if e.keyCode is 67 and e.ctrlKey
            close()
          console.log('5', @history.index)
          return false

        onClose: (dialog) =>
          @history.rollbackSearch()
          @$code_mirror.removeClass 'extra-dialog'
    )
    close.back = back
