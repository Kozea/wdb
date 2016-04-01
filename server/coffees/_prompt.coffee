# This file is part of wdb
#
# wdb Copyright (c) 2012-2016  Florian Mounier, Kozea
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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

    @code_mirror.on 'changes', @changes.bind @

    CodeMirror.registerHelper "hint", "jedi",
      (cm, callback, options) =>
        cur = cm.getCursor()
        tok = cm.getTokenAt(cur)
        return if cm.getValue().startsWith('.') and cm.getValue().length is 2
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
      'Shift-PageUp': =>
        @wdb.interpreter.scroll(-1)
      'Shift-PageDown': =>
        @wdb.interpreter.scroll(1)

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
    hints =
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
    CodeMirror.on hints, 'shown', =>
      if @code_mirror.state.completionActive.options.completeSingle
        cls = 'triggered'
      else
        cls = 'auto'
      $(@code_mirror.state.completionActive.widget.hints).addClass cls

    @completion.callback hints

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
        @history.commitSearch()
      ,
        bottom: true
        onInput: (e, val, close) =>
          return unless val
          @history.resetSearch()
          $('.CodeMirror-search-field').toggleClass(
            'not-found',
            val and not
            @history[if close.back then 'searchNext' else 'searchPrev'](val))
        onKeyDown: (e, val, close) =>
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
          return false

        onClose: (dialog) =>
          @history.rollbackSearch()
          @$code_mirror.removeClass 'extra-dialog'
    )
    close.back = back

  changes: ->
    @wdb.interpreter.scroll()
