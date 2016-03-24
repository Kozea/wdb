# This file is part of wdb
#
# wdb Copyright (C) 2012-2015 Florian Mounier, Kozea
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


class Wdb extends Log
  __version__: '2.9.99'

  constructor: ->
    super
    @started = false
    @cwd = null
    @file_cache = {}
    @last_cmd = null
    @eval_time = null

    @ws = new Websocket(@, $('[data-uuid]').attr('data-uuid'))
    @traceback = new Traceback @
    @cm = new Codemirror @
    @interpreter = new Interpreter @
    @prompt = new Prompt @
    @switch = new Switch @
    @watchers = new Watchers @

  opening: ->
    # Start by getting current trace
    if not @started
      $(window).on 'keydown', @global_key.bind @
      @started = true

    @ws.send 'Start'

  working: ->
    $('.activity').addClass('is-active')

  chilling: ->
    $('.activity').removeClass('is-active')

  done: (suggest=null)->
    @interpreter.scroll()
    @prompt.ready suggest
    @chilling()

  init: (data) ->
    if data.version isnt @constructor::__version__
      @print
        for: 'Client Server version mismatch !'
        result: "Server is #{@constructor::__version__} and
                 Client is #{data.version or '<= 2.0'}"

    @cwd = data.cwd
    brks = data.breaks
    for brk in brks
      @cm.breakpoints[brk.fn] ?= []
      @cm.breakpoints[brk.fn].push brk

  title: (data) ->
    $('.title')
      .text(data.title)
      .attr('title', data.title)

    $('.subtitle')
      .text(data.subtitle)
      .attr('title', data.subtitle)

  trace: (data) ->
    $('.trace').addClass('mdl-layout--fixed-drawer')
    @traceback.make_trace data.trace

  select_trace: (level) ->
    @ws.send 'Select', level

  selectcheck: (data) ->
    if data.name not of @file_cache
      @ws.send 'File', data.name
    else
      data.file = @file_cache[data.name]
      @select data

  select: (data) ->
    current_frame = data.frame
    $('.source-editor').removeClass('hidden')
    $('.interpreter').removeClass('full-height')
    $('.trace-line').removeClass('selected')
    $('.trace-' + current_frame.level).addClass('selected')
    @file_cache[data.name] = data.file
    @cm.open(data, current_frame)
    @done()

  ellipsize: ($code) ->
    $code.find('span.cm-string').each ->
      txt = $(@).text()
      if txt.length > 128
        $(@).text ''
        $(@).append $('<span class="short close">').text(txt.substr(0, 128))
        $(@).append $('<span class="long">').text(txt.substr(128))

  code: (parent, src, classes=[], html=false, title=null, mode="python") ->
    if html
      if src[0] != '<' or src.slice(-1) != '>'
        $node = $('<div>', class: 'out').html(src)
      else
        $node = $(src)
      parent.append $node
      $node.add($node.find('*')).contents().filter(->
        @nodeType == 3 and @nodeValue.length > 0 and
        not $(@parentElement).closest('thead').size()
      )
      .wrap('<code>')
      .parent()
      .each (i, elt) =>
        $code = $(elt)
        $code.addClass('waiting_for_hl').addClass('cm-s-default')
        for cls in classes
          $code.addClass(cls)
        $code.attr('title', title) if title
        setTimeout (=>
          CodeMirror.runMode $code.text(), mode, $code.get(0)
          $code.removeClass('waiting_for_hl')
          @ellipsize $code
        ), 50
    else
      $code = $('<code>', 'class': 'cm-s-default')
      for cls in classes
        $code.addClass(cls)
      $code.attr('title', title) if title
      parent.append $code
      CodeMirror.runMode src, mode, $code.get(0)
      @ellipsize $code

    $code

  execute: (snippet) ->
    cmd = =>
      @ws.send.apply @ws, arguments
      @last_cmd = arguments
      @working()

    if snippet.indexOf('.') == 0
      space = snippet.indexOf(' ')
      if space > -1
        key = snippet.substr(1, space - 1)
        data = snippet.substr(space + 1)
      else
        key = snippet.substr(1)
        data = ''
      switch key
        # when 'a' then @print_hist @session_cmd_hist[@cm.state.fn]
        when 'b' then @toggle_break data
        when 'c' then cmd 'Continue'
        when 'd' then cmd 'Dump', data if data
        when 'e' then @cm.toggle_edition()
        when 'f' then cmd 'Find', data if data
        when 'g' then @cls()
        when 'h' then @print_help()
        when 'i' then cmd 'Display', data if data
        when 'j' then cmd 'Jump', data if data
        when 'l' then cmd 'Breakpoints'
        when 'n' then cmd 'Next'
        when 'q' then cmd 'Quit'
        when 'r' then cmd 'Return'
        when 's' then cmd 'Step'
        when 't' then @toggle_break data, true
        when 'u' then cmd 'Until'
        when 'w' then cmd 'Watch', data if data
        when 'x' then cmd 'Diff', data if data
        when 'z' then @toggle_break data, false, true
      return

    else if snippet.indexOf('?') == 0
      cmd 'Dump', snippet.slice(1).trim()
      return

    else if snippet is '' and @last_cmd
      cmd.apply @, @last_cmd
      return
    if snippet
      @working()
      @ws.send 'Eval', snippet
      @eval_time = performance?.now()

  cls: ->
    @interpreter.clear()
    @done()

  print_hist: (hist) ->
    @print
      for: 'History'
      result: hist
        .slice(0)
        .reverse()
        .filter((e) -> e.indexOf('.') != 0)
        .join('\n')

  print_help: ->
    @print for: 'Supported commands', result: '''
.s or [Alt] + [↓] or [F11]     : \
 Step into
.n or [Alt] + [→] or [F10]     : \
 Step over (Next)
.r or [Alt] + [↑] or [F9]      : \
 Step out (Return)
.c or [Alt] + [Enter] or [F8]  : \
 Continue
.u or [Alt] + [←] or [F7]     : \
 Until (Next over loops)
.j lineno                      : \
 Jump to lineno (Must be at bottom frame and in the same function)
.b arg                         : \
 Set a session breakpoint  see below for what arg can be*
.t arg                         : \
 Set a temporary breakpoint, arg follow the same syntax as .b
.z arg                         : \
 Delete existing breakpoint
.l                             : \
 List active breakpoints
.a                             : \
 Echo all typed commands in the current debugging session
.d expression                  : \
 Dump the result of expression in a table
.w expression                  : \
 Watch expression in curent file (Click on the name to remove)
.q                             : \
 Quit
.h                             : \
 Get some help
.e                             : \
 Toggle file edition mode
.g                             : \
 Clear prompt
.i [mime/type;]expression      : \
 Display the result in an embed, mime type defaults to "text/html"
.x left ? right                : \
 Display the difference between the pretty print of 'left' and 'right'
.x left <> right               : \
 Display the difference between the repr of 'left' and 'right'
.f key in expression           : \
 Search recursively the presence of key in expression object tree
.f test of expression          : \
 Search recursively values that match test in expression inner tree.
 i.e.: .f type(x) == int of sys

All the upper commands are prefixed with a dot and can be \
executed with [Alt] + [the command letter], i.e.: [Alt] + [h]

iterable!sthg                  : \
 If cutter is installed, executes cut(iterable).sthg
expr >! file                   : \
 Write the result of expr in file
!< file                        : \
 Eval the content of file
[Enter]                        : \
 Eval the current selected text in page, useful to eval code in the source
[Shift] + [Enter]              : \
 Insert the current selected text in page in the prompt
[Ctrl] + [Enter]               : \
 Multiline prompt or execute if already in multiline mode.

* arg is using the following syntax:
    [file/module][:lineno][#function][,condition]
which means:
    - [file]                    : \
 Break if any line of `file` is executed
    - [file]:lineno             : \
 Break on `file` at `lineno`
    - [file][:lineno],condition : \
 Break on `file` at `lineno` if `condition` is True (ie: i == 10)
    - [file]#function           : \
 Break when inside `function` function
File is always current file by default and you can also \
specify a module like `logging.config`.
'''

  print: (data) ->
    if @eval_time
      duration = parseInt((performance.now() - @eval_time) * 1000)
      print_start = performance.now()
      @eval_time = null

    $group = $('<div>', class: 'printed scroll-line')
    @interpreter.write $group

    $group.append($timeholder = $('<div>'))
    @code($group, data.for, ['for prompted'])
    $result = $('<div>', class: 'result')
    $group.append($result)
    @code($result, data.result or ' ', ['val'], true)

    print_duration = parseInt((performance.now() - print_start) * 1000)
    @code($timeholder,
      @pretty_time(data.duration),
      ['duration'], false, "Total #{@pretty_time(duration)} + #{
        @pretty_time(print_duration)} of rendering") if data.duration

    @done(data.suggest)

  echo: (data) ->
    $group = $('<div>', class: 'echoed scroll-line')
    @interpreter.write $group
    @code($group, data.for, ['for prompted'])
    $result = $('<div>', class: 'result')
    $group.append($result)
    @code($result, data.val or '', ['val'], true, null, data.mode)
    @done()

  rawhtml: (data) ->
    $group = $('<div>', class: 'rawhtml scroll-line')
    @interpreter.write $group
    @code($group, data.for, ['for prompted'])
    @interpreter.write data.val
    @done()

  dump: (data) ->
    $group = $('<div>', class: 'dump scroll-line')
    @interpreter.write $group
    @code($group, data.for, ['for prompted'])

    $container = $('<div>')
    $table = $('<table>', class: 'mdl-data-table mdl-js-data-table
      mdl-shadow--2dp object')
      .appendTo($container)
    $core_head =
      $('<thead>', class: 'toggle closed').append(
        $('<tr>')
          .append($('<th>', class: 'core', colspan: 2)
          .text('Core Members'))).appendTo($table)
    $core_tbody = $('<tbody>', class: 'core closed').appendTo($table)

    $method_head =
      $('<thead>', class: 'toggle closed').append(
        $('<tr>')
          .append($('<th>', class: 'method', colspan: 2)
          .text('Methods'))).appendTo($table)
    $method_tbody = $('<tbody>', class: 'method closed').appendTo($table)

    $attr_head =
      $('<thead>', class: 'toggle closed').append(
        $('<tr>').append(
          $('<th>', class: 'attr', colspan: 2)
            .text('Attributes'))).appendTo($table)
    $attr_tbody = $('<tbody>', class: 'attr closed').appendTo($table)

    for key, val of data.val
      $tbody = $attr_tbody
      if key.indexOf('__') == 0 and key.indexOf('__', key.length - 2) != -1
        $tbody = $core_tbody
      else if val.type.indexOf('method') != -1
        $tbody = $method_tbody

      $tbody.append($('<tr>')
        .append(
          $('<td>', class: 'mdl-data-table__cell--non-numeric key').text(key))
        .append($('<td>', class: 'val').html(val.val)))

    if $core_tbody.find('tr').size() is 0
      $core_head.remove()
      $core_tbody.remove()

    if $attr_tbody.find('tr').size() is 0
      $attr_head.remove()
      $attr_tbody.remove()

    if $method_tbody.find('tr').size() is 0
      $method_head.remove()
      $method_tbody.remove()

    if data.doc
      $table.append(
        $('<thead>', class: 'toggle closed').append(
          $('<tr>').append(
            $('<th>', class: 'doc', colspan: 2)
              .text('Documentation'))))

      $('<tbody>', class: 'doc closed').append(
        $('<tr>').append(
          $('<td>', class: 'mdl-data-table__cell--non-numeric doc', colspan: 2)
            .text(data.doc))).appendTo($table)

    if data.source
      $table.append(
        $('<thead>', class: 'toggle closed').append(
          $('<tr>').append(
            $('<th>', class: 'source', colspan: 2)
              .text('Source'))))

      $('<tbody>', class: 'source closed').append(
        $('<tr>').append(
          $('<td>',
            class: 'mdl-data-table__cell--non-numeric source',
            colspan: 2)
              .text(data.source))).appendTo($table)

    componentHandler.upgradeElement($table.get(0))
    @code($group, $container.html(), [], true)
    @done()

  breakset: (data) ->
    @cm.set_breakpoint data

    if @prompt.get()[0] is '.' and @prompt.get()[1] in ['b', 't']
      @done()
    else
      @chilling()

  breakunset: (data) ->
    @cm.clear_breakpoint data

    if @prompt.get()[0] is '.' and @prompt.get()[1] in ['b', 't', 'z']
      @done()
    else
      @chilling()

  split: (str, char) ->
    # Returns the split on last occurence of char
    if char in str
      split = str.split(char)
      [split[0], split.slice(1).join(char).trim()]
    else
      [str, null]

  toggle_break: (arg, temporary=false, remove_only=false) ->
    brk =
      lno: null
      cond: null
      fun: null
      fn: null
      temporary: temporary

    remaining = arg

    [remaining, brk.cond] = @split remaining, ','
    [remaining, brk.fun] = @split remaining, '#'
    [remaining, brk.lno] = @split remaining, ':'
    brk.fn = remaining or @cm.state.fn
    brk.lno = parseInt(brk.lno) or null

    exist = false
    for ebrk in @cm.breakpoints[brk.fn] or []
      if (ebrk.fn is brk.fn and
         ebrk.lno is brk.lno and
         ebrk.cond is brk.cond and
         ebrk.fun is brk.fun and
         (ebrk.temporary is brk.temporary or remove_only)
      )
        exist = true
        brk = ebrk
        break

    if exist or remove_only
      @cm.clear_breakpoint(brk)
      cmd = 'Unbreak'
      unless brk.temporary
        cmd = 'Broadcast|' + cmd
      @ws.send cmd, brk
      @working()
      return

    if brk.lno
      @cm.ask_breakpoint(brk.lno)
    cmd = 'Break'
    unless temporary
      cmd = 'Broadcast|' + cmd
    @ws.send cmd, brk
    @working()

  watched: (data) ->
    @watchers.updateAll data
    # No @done() here

  ack: ->
    @done()

  display: (data) ->
    $group = $('<div>', class: 'display scroll-line')
    @interpreter.write $group
    @code($group, data.for, ['for prompted'])
    if data.type.indexOf('image') >= 0
      $tag = $("<img>")
    else if data.type.indexOf('audio') >= 0
      $tag = $("<audio>", controls: 'controls', autoplay: 'autoplay')
    else if data.type.indexOf('video') >= 0 or data.type.indexOf('/ogg') >= 0
      $tag = $("<video>", controls: 'controls', autoplay: 'autoplay')
    else
      $tag = $("<iframe>")

    $tag.addClass('display')
    $tag.attr('src', "data:#{data.type};charset=UTF-8;base64,#{data.val}")
    $group.append($tag)
    @done()

  suggest: (data) ->
    @prompt.complete data if data

  die: ->
    @title(title: 'Dead', subtitle: 'Program has exited')
    @ws.ws.close()
    setTimeout (-> window.close()), 10

  global_key: (e) ->
    return true if @cm.rw

    if e.altKey and (
      65 <= e.keyCode <= 90 or 37 <= e.keyCode <= 40 or e.keyCode is 13
    ) or 118 <= e.keyCode <= 122
      char = switch e.keyCode
        when 37, 118 then 'u' # <     / F7
        when 13, 119 then 'c' # Enter / F8
        when 38, 120 then 'r' # ^     / F9
        when 39, 121 then 'n' # >     / F10
        when 40, 122 then 's' # v     / F11
        else String.fromCharCode(e.keyCode)
      char = char.toLowerCase()
      extra = ''
      # Break on current line
      if char in ['b', 't', 'z']
        extra += ' :' + @cm.state.lno
      if char is 'i'
        extra = getSelection().toString()

      @execute '.' + char + extra
      return false

    if e.keyCode is 13
      sel = getSelection().toString()
      return unless sel
      if e.shiftKey
        @eval_insert sel
      else
        @prompt.history.historize sel
        @execute sel
      return false

  newline: ->
    @prompt.ready('', true)
    @chilling()

  inspect: (id) ->
    @ws.send 'Inspect', id
    @working()
    false

  unwatch: (expr) ->
    @ws.send 'Unwatch', expr
    @working()

  paste_target: (e) ->
    return unless e.which == 2 # Middle
    target = $(e.target).text().trim()
    @prompt.history.historize target
    @ws.send 'Dump', target
    @working()
    false

  disable: ->
    @ws.send 'Disable'

  shell: ->
    $('.trace').removeClass('mdl-layout--fixed-drawer')
    $('.source-editor').addClass('hidden')
    $('.interpreter').addClass('full-height')
    @done()

  dialog: (title, content) ->
    $('.modals').append $dialog = $("""
      <dialog class="mdl-dialog">
        <h3 class="mdl-dialog__title">#{ title }</h3>
        <div class="mdl-dialog__content">
          #{ content }
        </div>
        <div class="mdl-dialog__actions">
          <button type="button" class="mdl-button dialog-close">Close</button>
        </div>
      </dialog>
    """)
    $dialog.find('.dialog-close').on 'click', ->
      $dialog.get(0).close()
      $dialog.remove()

    $dialog.get(0).showModal()

  pretty_time: (time) ->
    if time < 1000
      return "#{time}μs"

    time = time / 1000
    if time < 10
      return "#{time.toFixed(2)}ms"
    if time < 100
      return "#{time.toFixed(1)}ms"
    if time < 1000
      return "#{time.toFixed(0)}ms"

    time = time / 1000
    if time < 10
      return "#{time.toFixed(2)}s"
    if time < 100
      return "#{time.toFixed(1)}s"

    "#{time.toFixed(0)}s"


$ => @wdb = new Wdb()
