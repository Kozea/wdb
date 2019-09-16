# This file is part of wdb
#
# wdb Copyright (C) 2012-2016 Florian Mounier, Kozea
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
  __version__: '3.3.0'

  constructor: ->
    super()
    @started = false
    @cwd = null
    @file_cache = {}
    @last_cmd = null
    @evalTime = null

    @ws = new Websocket(@, $('[data-uuid]').attr('data-uuid'))
    @traceback = new Traceback @
    @source = new Source @
    @interpreter = new Interpreter @
    @prompt = new Prompt @
    @switch = new Switch @
    @watchers = new Watchers @

    @$patience = $('.patience')
    # Prevent locking of monothread
    $(window).on 'beforeunload', @unload.bind @

  opening: ->
    # Start by getting current trace
    if not @started
      $(window).on 'keydown', @global_key.bind @
      @started = true

    @ws.send 'Start'
    @switch.open_term()

  working: ->
    $('body,.activity').addClass('is-active')

  chilling: ->
    $('body,.activity').removeClass('is-active')

  done: ->
    @interpreter.scroll()
    @prompt.ready()
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
      @source.breakpoints[brk.fn] ?= []
      @source.breakpoints[brk.fn].push brk

  title: (data) ->
    $('.title')
      .text(data.title)
      .attr('title', data.title)

    $('.subtitle')
      .text(data.subtitle)
      .attr('title', data.subtitle)

  trace: (data) ->
    @switch.open_trace()
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
    @switch.open_code()
    $('.trace-line').removeClass('selected')
    $('.trace-' + current_frame.level).addClass('selected')
    @file_cache[data.name] = data.file
    @source.open(data, current_frame)
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
        not $(@parentElement).closest('thead').length
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
      sent = switch key
        when 'a' then @printHistory()
        when 'b' then @toggle_break data
        when 'c' then cmd 'Continue'
        when 'd' then cmd 'Dump', data if data
        when 'e' then @source.toggle_edition()
        when 'f' then cmd 'Find', data if data
        when 'g' then @cls()
        when 'h' then @printHelp()
        when 'i' then cmd 'Display', data if data
        when 'j' then cmd 'Jump', data if data
        when 'k' then @clearHistory()
        when 'l' then cmd 'Breakpoints'
        when 'm' then cmd 'Restart'
        when 'n' then cmd 'Next'
        when 'o' then @source.external(not data)
        when 'q' then cmd 'Quit'
        when 'r' then cmd 'Return'
        when 's' then cmd 'Step'
        when 't' then @toggle_break data, true
        when 'u' then cmd 'Until'
        when 'w' then cmd 'Watch', data if data
        when 'x' then cmd 'Diff', data if data
        when 'z' then @toggle_break data, false, true

      @prompt.unlock() unless sent
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
      @evalTime = performance?.now()
      @$patience.text(@pretty_time(0))
      raf = =>
        unless @evalTime
          @$patience.text('')
          return
        duration = parseInt((performance.now() - @evalTime) * 1000)
        @$patience.text(@pretty_time(duration))
        requestAnimationFrame raf
      requestAnimationFrame raf

  cls: ->
    @interpreter.clear()
    @done()

  printHistory: (hist) ->
    @print
      for: 'History'
      result: @prompt.history.getSessionHistory()
        .reverse()
        .filter((e) -> e.indexOf('.') != 0)
        .join('\n')

  clearHistory: ->
    @prompt.history.clear()

  printHelp: ->
    @dialog 'Help', help
    @done()

  print: (data) ->
    if @evalTime
      duration = parseInt((performance.now() - @evalTime) * 1000)
      print_start = performance.now()
      @evalTime = null

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

    @done()

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
          $('<td>', class: 'key').text(key))
        .append($('<td>', class:
          'mdl-data-table__cell--non-numeric val').html(val.val)))

    if $core_tbody.find('tr').length is 0
      $core_head.remove()
      $core_tbody.remove()

    if $attr_tbody.find('tr').length is 0
      $attr_head.remove()
      $attr_tbody.remove()

    if $method_tbody.find('tr').length is 0
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
    @source.set_breakpoint data

    if @prompt.get()[0] is '.' and @prompt.get()[1] in ['b', 't']
      @done()
    else
      @chilling()

  breakunset: (data) ->
    @source.clear_breakpoint data

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
    brk.fn = remaining or @source.state.fn
    brk.lno = parseInt(brk.lno) or null

    exist = false
    for ebrk in @source.breakpoints[brk.fn] or []
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
      @source.clear_breakpoint(brk)
      cmd = 'Unbreak'
      unless brk.temporary
        cmd = 'Broadcast|' + cmd
      @ws.send cmd, brk
      @working()
      return

    if brk.lno
      @source.ask_breakpoint(brk.lno)
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
    $('body').addClass 'is-dead'
    unless $('body').attr('data-debug')
      setTimeout (-> window.close()), 10

  global_key: (e) ->
    return true if @source.rw
    sel = @source.focused() and @source.code_mirror.getSelection()

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
        extra += ' :' + @source.state.lno
      if char is 'i'
        extra = ' ' + sel
      if char is 'o' and e.shiftKey
        extra = ' ' + '!'

      @execute '.' + char + extra
      return false

    if e.keyCode is 13
      return if @prompt.focused()
      return unless sel

      if e.shiftKey
        @prompt.insert sel
        @prompt.focus()
      else if e.ctrlKey
        @ws.send 'Watch', sel
      else
        @prompt.history.historize sel
        @execute sel
      return false

  newline: ->
    @prompt.ready true
    @chilling()

  inspect: (id) ->
    @ws.send 'Inspect', id
    @working()
    false

  unwatch: (expr) ->
    @ws.send 'Unwatch', expr
    @working()

  paste_target: (e) ->
    target = $(e.target).text().trim()
    return true if target is ''
    if e.shiftKey
      @prompt.insert target
      return
    if e.ctrlKey
      @ws.send 'Watch', target
      return
    @prompt.history.historize target
    @ws.send 'Dump', target
    @working()
    false

  disable: ->
    @ws.send 'Disable'

  shell: ->
    @switch.close_trace()
    @switch.close_code()
    @switch.open_term()
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

    $dialog.find('.mdl-tabs,.mdl-data-table').each ->
      componentHandler.upgradeElement @
    $dialog.on 'close', =>
      @prompt.ready()

    dialog = $dialog.get(0)
    dialogPolyfill?.registerDialog(dialog)
    dialog.showModal()

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
    if time < 60
      return "#{time.toFixed(1)}s"

    with_zero = (s) ->
      s = s.toString()
      if s.length is 1
        return "0#{s}"
      s

    mtime = Math.floor(time / 60)
    stime = (time - 60 * mtime).toFixed(0)

    if mtime < 60
      return "#{mtime}m#{with_zero(stime)}s"

    htime = Math.floor(mtime / 60)
    mtime = (mtime - 60 * htime).toFixed(0)
    "#{htime}h#{with_zero(mtime)}m#{with_zero(stime)}s"


  unload: ->
    @ws.ws.close()

$ -> window.wdb = new Wdb()
