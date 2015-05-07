# This file is part of wdb
#
# wdb Copyright (C) 2012  Florian Mounier, Kozea
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
  __version__: '2.1.1'

  constructor: ->
    super
    @started = false
    @to_complete = null
    @cwd = null
    @backsearch = null
    @cmd_hist = []
    @session_cmd_hist = {}
    @file_cache = {}
    @last_cmd = null
    @eval_time = null

    @waited_for_ws = 0

    # Page elements
    @$activity = $('#activity')
    @$title = $('#title')
    @$waiter = $('#waiter')
    @$wdb = $('#wdb')
    @$source = $('#source')
    @$interpreter = $('#interpreter')
    @$scrollback = $('#scrollback')
    @$prompt = $('#prompt')
    @$eval = $('#eval')
    @$completions = $('#completions')
    @$backsearch = $('#backsearch')
    @$traceback = $('#traceback')
    @$watchers = $('#watchers')

    try
      @cmd_hist = JSON.parse(localStorage['cmd_hist'])
    catch e
      @fail e

    @ws = new Websocket(@, @$wdb.find('> header').attr('data-uuid'))
    @cm = new Codemirror(@)

  opening: ->
    # Start by getting current trace
    if not @started
      @$eval
        .on 'keydown', @eval_key.bind @
        .on 'keyup', @eval_carret_change.bind @
        .on 'mouseup', @eval_carret_change.bind @
        .on 'blur', @searchback_stop.bind @

      $(window).on 'keydown', @global_key.bind @

      @$traceback.on 'click', '.traceline', @select_click.bind @
      @$scrollback.add(@$watchers)
        .on 'click', 'a.inspect', @inspect.bind(@)
        .on 'click', '.short.close', @short_open.bind @
        .on 'click', '.short.open', @short_close.bind @
        .on 'click', '.toggle', @toggle_visibility.bind @

      @$watchers.on 'click', '.watching .name', @unwatch.bind @
      @$source.find('#source-editor').on 'mouseup', @paste_target.bind @
      $('#deactivate').click @disable.bind @
      @$interpreter.on 'keydown', (e) =>
        if e.ctrlKey and 37 <= e.keyCode <= 40 or
           118 <= e.keyCode <= 122 or e.keyCode is 13
          return true

        if e.shiftKey and e.keyCode in [33, 34]
          scroll = @$interpreter.height() * 2 / 3
          way = if e.keyCode is 33 then -1 else 1

          @$interpreter
            .stop(true, true)
            .animate((scrollTop: @$interpreter.scrollTop() + way * scroll), 500)
          return false

        @$eval.focus()

      false

      @started = true

    @ws.send 'Start'
    @$waiter.remove()
    @$wdb.show()
    @$eval.autosize()

  working: ->
    @$activity.addClass 'on'

  chilling: ->
    @$activity.removeClass 'on'

  done: (suggest=null)->
    @termscroll()
    eval_val = suggest or ''
    if @$eval.val() isnt eval_val
      @$eval.val(eval_val)
        .prop('disabled', false)
        .attr('data-index', -1)
        .trigger('autosize.resize')
        .focus()
    @$completions.attr('style', '')
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
    @$title
      .text(data.title)
      .attr('title', data.title)
      .append(
        $('<small>')
          .text(data.subtitle)
          .attr('title', data.subtitle))

  trace: (data) ->
    @$traceback.removeClass('hidden')
    @$traceback.empty()
    for frame in data.trace
      $traceline = $('<div>')
        .addClass('traceline')
        .attr('id', 'trace-' + frame.level)
        .attr('data-level', frame.level)

      for brk in @cm.breakpoints[frame.file] or []
        unless brk.cond or brk.fun or brk.lno
          $traceline.addClass('breakpoint')
          break

      if frame.current
        $traceline.addClass('real-selected')
      $tracefile = $('<span>').addClass('tracefile').text(frame.file)
      $tracelno = $('<span>').addClass('tracelno').text(frame.lno)
      $tracefun = $('<span>').addClass('tracefun').text(frame.function)

      $tracefilelno = $('<div>')
        .addClass('tracefilelno')
        .append($tracefile)
        .append($tracelno)

      $tracefunfun = $('<div>')
        .addClass('tracefunfun')
        .append($tracefun)

      if frame.file.indexOf('site-packages') > 0
        suffix = frame.file.split('site-packages').slice(-1)[0]
        $tracefile.text(suffix)
        $tracefile.prepend(
          $('<span>')
            .addClass('tracestar')
            .text('*')
            .attr(title: frame.file))

      if frame.file.indexOf(@cwd) == 0
        suffix = frame.file.split(@cwd).slice(-1)[0]
        $tracefile.text(suffix)
        $tracefile.prepend(
          $('<span>')
            .addClass('tracestar')
            .text('.')
            .attr(title: frame.file))

      $tracecode = $('<div>').addClass('tracecode')

      @code $tracecode, frame.code
      $traceline.append $tracefilelno
      $traceline.append $tracecode
      $traceline.append $tracefunfun
      @$traceback.prepend $traceline

  select_click: (e) ->
    @ws.send 'Select', $(e.currentTarget).attr('data-level')

  selectcheck: (data) ->
    if data.name not of @file_cache
      @ws.send 'File', data.name
    else
      data.file = @file_cache[data.name]
      @select data

  select: (data) ->
    current_frame = data.frame
    @$interpreter.show()
    @$source.find('#source-editor').removeClass('hidden')
    $('.traceline').removeClass('selected')
    $('#trace-' + current_frame.level).addClass('selected')
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
        $code.addClass('waiting_for_hl').addClass('CodeMirror-standalone')
        for cls in classes
          $code.addClass(cls)
        $code.attr('title', title) if title
        setTimeout (=>
          CodeMirror.runMode $code.text(), mode, $code.get(0)
          $code.removeClass('waiting_for_hl')
          @ellipsize $code
        ), 50
    else
      $code = $('<code>', 'class': 'CodeMirror-standalone')
      for cls in classes
        $code.addClass(cls)
      $code.attr('title', title) if title
      parent.append $code
      CodeMirror.runMode src, mode, $code.get(0)
      @ellipsize $code

    $code

  historize: (snippet) ->
    if not (@cm.state.fn of @session_cmd_hist)
      @session_cmd_hist[@cm.state.fn] = []

    while (index = @cmd_hist.indexOf(snippet)) != -1
      @cmd_hist.splice(index, 1)

    @cmd_hist.unshift snippet
    @session_cmd_hist[@cm.state.fn].unshift snippet

    localStorage and localStorage['cmd_hist'] = JSON.stringify @cmd_hist

  execute: (snippet) ->
    console.log snippet
    snippet = snippet.trim()
    @historize snippet

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
        when 'a' then @print_hist @session_cmd_hist[@cm.state.fn]
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
      @suggest_stop()
      return

    else if snippet is '' and @last_cmd
      cmd.apply @, @last_cmd
      return
    if snippet
      @working()
      @ws.send 'Eval', snippet
      @$eval.val(@$eval.val() + '...')
        .trigger('autosize.resize')
        .prop('disabled', true)
      @eval_time = performance?.now()

  cls: ->
    @$scrollback.empty()
    @searchback_stop()
    @suggest_stop()
    @multiline_stop()
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

  termscroll: ->
    @$interpreter
      .stop(true)
      .animate((scrollTop: @$scrollback.height()), 1000)

  print: (data) ->
    if performance and @eval_time
      duration = parseInt((performance.now() - @eval_time) * 1000)
      @eval_time = null

    @suggest_stop()
    snippet = @$eval.val()
    $group = $('<div>')
    @$scrollback.append($group)

    @code($group,
      @pretty_time(data.duration),
      ['duration'], false, "Total #{@pretty_time(duration)}") if data.duration
    @code($group, data.for, ['prompted'])
    @code(@$scrollback, data.result, [], true)
    @done(data.suggest)

  echo: (data) ->
    @code(@$scrollback, data.for, ['prompted'])
    @code(@$scrollback, data.val or '', [], true, null, data.mode)
    @done()

  rawhtml: (data) ->
    @code(@$scrollback, data.for, ['prompted'])
    @$scrollback.append(data.val)
    @done()

  dump: (data) ->
    @code(@$scrollback, data.for, ['prompted'])
    $container = $('<div>')
    $table = $('<table>', class: 'object').appendTo($container)
    $core_head =
      $('<thead>', class: 'toggle closed').append(
        $('<tr>')
          .append($('<td>', class: 'core', colspan: 2)
          .text('Core Members'))).appendTo($table)
    $core_tbody = $('<tbody>', class: 'core closed').appendTo($table)

    $method_head =
      $('<thead>', class: 'toggle closed').append(
        $('<tr>')
          .append($('<td>', class: 'method', colspan: 2)
          .text('Methods'))).appendTo($table)
    $method_tbody = $('<tbody>', class: 'method closed').appendTo($table)

    $attr_head =
      $('<thead>', class: 'toggle closed').append(
        $('<tr>').append(
          $('<td>', class: 'attr', colspan: 2)
            .text('Attributes'))).appendTo($table)
    $attr_tbody = $('<tbody>', class: 'attr closed').appendTo($table)

    for key, val of data.val
      $tbody = $attr_tbody
      if key.indexOf('__') == 0 and key.indexOf('__', key.length - 2) != -1
        $tbody = $core_tbody
      else if val.type.indexOf('method') != -1
        $tbody = $method_tbody

      $tbody.append($('<tr>')
        .append($('<td>').text(key))
        .append($('<td>').html(val.val)))

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
            $('<td>', class: 'doc', colspan: 2)
              .text('Documentation'))))

      $('<tbody>', class: 'doc closed').append(
        $('<tr>').append(
          $('<td>', class: 'doc', colspan: 2)
            .text(data.doc))).appendTo($table)

    if data.source
      $table.append(
        $('<thead>', class: 'toggle closed').append(
          $('<tr>').append(
            $('<td>', class: 'source', colspan: 2)
              .text('Source'))))

      $('<tbody>', class: 'source closed').append(
        $('<tr>').append(
          $('<td>', class: 'source', colspan: 2)
            .text(data.source))).appendTo($table)

    @code(@$scrollback, $container.html(), [], true)
    @done()

  breakset: (data) ->
    @cm.set_breakpoint data
    if not data.lno and not data.fun and not data.cond
      @$traceback.find("[title=\"#{data.fn}\"]")
        .closest('.traceline')
        .addClass('breakpoint')

    if @$eval.val()[0] is '.' and @$eval.val()[1] in ['b', 't']
      @done()
    else
      @chilling()

  breakunset: (data) ->
    @cm.clear_breakpoint data
    if not data.lno and not data.fun and not data.cond
      @$traceback.find("[title=\"#{data.fn}\"]")
        .closest('.traceline')
        .removeClass('breakpoint')

    if @$eval.val()[0] is '.' and @$eval.val()[1] in ['b', 't', 'z']
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

  format_fun: (p) ->
    tags = [
      $('<span>', class: 'fun_name', title: p.module).text(p.call_name),
      $('<span>', class: 'fun_punct').text('(')]
    for param, i in p.params
      cls = 'fun_param'
      if i == p.index or (i == p.params.length - 1 and p.index > i)
        cls = 'fun_param active'
      tags.push $('<span>', class: cls).text(param)
      if i != p.params.length - 1
        tags.push $('<span>', class: 'fun_punct').text(', ')

    tags.push $('<span>', class: 'fun_punct').text(')')
    tags

  suggest: (data) ->
    if data
      $comp = @$completions.find('table').empty()
      $comp.append($('<thead><tr><th id="comp-desc" colspan="5">'))
      height = @$completions.height()
      added = []
      for param in data.params
        $('#comp-desc').append(@format_fun(param))

      if data.completions.length
        $tbody = $('<tbody>')
        base_len = data.completions[0].base.length
        txtarea = @$eval.get(0)
        startPos = txtarea.selectionStart
        @$eval.data
          start: @$eval.val().substr(0, startPos - base_len)
          end: @$eval.val().substr(startPos)
      for completion, index in data.completions
        if (completion.base + completion.complete) in added
          continue
        added.push(completion.base + completion.complete)
        if index % 5 == 0
          $tbody.append($appender = $('<tr>'))

        $appender.append($td = $('<td>').attr('title', completion.description)
          .append($('<span>').addClass('base').text(completion.base))
          .append($('<span>').addClass('completion').text(completion.complete)))
        if not completion.complete
          $td.addClass('complete')
          $('#comp-desc').html($td.attr('title'))
      $comp.append($tbody)
      @$completions.height(Math.max(height, $comp.height()))
      @termscroll()

    # Complete queued completion
    if @to_complete
      @ws.send 'Complete', @to_complete
      # Marking it with false -> waiting for suggest
      @to_complete = false
    else
      # Making completion available
      @to_complete = null

  suggest_stop: ->
    if @$completions.find('table td,table tr').size()
      @$completions.find('table').empty()
      true
    else
      false

  watched: (data) ->
    for own watcher, value of data
      $watcher = @$watchers
        .find(".watching")
        .filter((e) -> $(e).attr('data-expr') == watcher)
      if not $watcher.size()
        $name = $('<code>', class: "name")
        $value = $('<div>', class: "value")
        @$watchers.append(
          $watcher = $('<div>', class: "watching")
            .attr('data-expr', watcher)
            .append($name.text(watcher), $('<code>').text(': '), $value))
        @code($value, value.toString(), [], true)
      else
        $watcher.find('.value code').remove()
        @code($watcher.find('.value'), value.toString(), [], true)
      $watcher.addClass('updated')
    @$watchers.find('.watching:not(.updated)').remove()
    @$watchers.find('.watching').removeClass('updated')
    @done()

  ack: ->
    @$eval.val('').trigger('autosize.resize')

  display: (data) ->
    @suggest_stop()
    snippet = @$eval.val()
    @code(@$scrollback, data.for, ['prompted'])
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
    @$scrollback.append($tag)
    @done()

  searchback: ->
    @suggest_stop()
    index = @backsearch
    val = @$eval.val()
    for h in @cmd_hist
      re = new RegExp('(' + val + ')', 'gi')
      if re.test(h)
        index--
        if index == 0
          @$backsearch
            .html(h.replace(re, '<span class="backsearched">$1</span>'))
          return
    if @backsearch == 1
      @searchback_stop()
      return
    @backsearch = Math.max(@backsearch - 1, 1)

  searchback_stop: (validate) ->
    if @backsearch
      if validate is true
        @$eval
          .val(@$backsearch.text())
          .trigger('autosize.resize')
      @$backsearch.html('')
      @backsearch = null
      true
    else
      false

  die: ->
    $('h1').html('Dead<small>Program has exited</small>')
    @ws.ws.close()
    setTimeout (-> window.close()), 10

  multiline_stop: ->
    if @$prompt.hasClass('multiline')
      @$prompt.removeClass('multiline')
      true
    else
      false

  global_key: (e) ->
    return true if @cm.rw

    if e.altKey and (
      65 <= e.keyCode <= 90 or 37 <= e.keyCode <= 40 or e.keyCode is 13
      ) or 119 <= e.keyCode <= 122
      char = switch e.keyCode
        when 13, 119 then 'c' # Enter / F7
        when 37, 118 then 'u' # <     / F8
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
        @historize sel
        @execute sel
      return false

  eval_key: (e) ->
    if e.altKey and e.keyCode is 82 and @backsearch # R
      @backsearch = Math.max(@backsearch - 1, 1)
      @searchback()
      return false

    return if e.altKey

    if e.ctrlKey
      switch e.keyCode
        when 13 # Enter
          if @$prompt.hasClass('multiline')
            @$prompt.removeClass('multiline')
            @execute @$eval.val()
            return false
          @$prompt.addClass('multiline')
          @eval_insert('\n')
          return true

        when 82 # R
          @backsearch ?= 0
          if e.shiftKey
            @backsearch = Math.max(@backsearch - 1, 1)
          else
            @backsearch++
          @searchback()
          return false
        when 67 # C
          @searchback_stop()
          return false
        when 68 # D
          @ws.send 'Quit'
          return false

        when 32 # Space
          @eval_move_suggest 1, true

    switch e.keyCode
      when 13 # Enter
        if @backsearch
          @searchback_stop true
          return false
        $table = @$completions.find('table')
        if $table.find('td.active').size() and
           not $table.find('td.complete').size()
          @suggest_stop()
          return false
        unless @$prompt.hasClass('multiline')
          @execute @$eval.val()
          return false

      when 27 # Escape
        @searchback_stop() or @suggest_stop() or @multiline_stop()
        return false

      when 9, 39 # Tab, Right
        eof = @$eval.get(0).selectionStart is @$eval.val().length
        multiline = @$prompt.hasClass('multiline')
        if e.keyCode is 9 and multiline
          @eval_insert('  ')
          return false
        unless e.keyCode is 39 and not eof and not multiline
          return false if @backsearch
          if @eval_move_suggest (
            unless e.shiftKey then 1 else -1), not multiline
            return false
        return true

      when 37  # Left
        if @eval_move_suggest -1
          return false
        return true

      when 38  # Up
        if @eval_move_suggest -5
          return false
        return true if @$prompt.hasClass('multiline')
        @eval_move_history 1
        return false

      when 40  # Down
        if @eval_move_suggest 5
          return false
        return true if @$prompt.hasClass('multiline')
        @eval_move_history -1
        return false

  eval_insert: (char) ->
    txtarea = @$eval.get(0)
    startPos = txtarea.selectionStart
    endPos = txtarea.selectionEnd
    @$eval.val(
      @$eval.val().substring(0, startPos) +
      char +
      @$eval.val().substring(endPos, @$eval.val().length)
    )
    txtarea.setSelectionRange(startPos + char.length, startPos + char.length)
    @$eval.trigger('autosize.resize')

  eval_move_suggest: (shift, trigger=false) ->
    $tds = @$completions.find('table td')
    $active = $tds.filter('.active')
    return false unless $tds.length
    unless $active.length
      return false unless trigger
      $active = $tds.first().addClass('active')
    else
      index = $tds.index($active)
      index += shift
      if index < 0
        index = $tds.length - 1
      if index >= $tds.length
        index = 0
      $active.removeClass('active complete')
      $active = $tds.eq(index).addClass('active')
    base = $active.find('.base').text()
    completion = $active.find('.completion').text()
    root = @$eval.data().start + base + completion
    @$eval
      .val(root + @$eval.data().end)
    @$eval.get(0).setSelectionRange(root.length, root.length)
    @$eval.trigger('autosize.resize')
    $('#comp-desc').text($active.attr('title'))
    @termscroll()
    true

  eval_move_history: (shift) ->
    index = parseInt(@$eval.attr('data-index')) + shift
    if index >= -1 and index < @cmd_hist.length
      if index is -1
        to_set = @$eval.attr('data-current')
      else
        to_set = @cmd_hist[index]
      if index is 0 and shift is 1
        @$eval.attr('data-current', @$eval.val())

      @$eval.val(to_set)
        .attr('data-index', index).trigger('autosize.resize')
      @suggest_stop()
      @termscroll()

  eval_before_cursor: ->
    txtarea = @$eval.get(0)
    startPos = txtarea.selectionStart
    @$eval.val().substring(0, startPos)

  eval_carret_change: (e) ->
    if @$completions.find('table td').filter('.active').size()
      eof = @$eval.get(0).selectionStart is @$eval.val().length
      multiline = @$prompt.hasClass('multiline')

      unless e.keyCode and e.keyCode < 27 or 37 <= e.keyCode <= 40 or (
        e.ctrlKey and e.keyCode is 32)
        @suggest_stop()
      return

    txt = @eval_before_cursor()
    if @backsearch
      if not txt
        @searchback_stop()
      else
        @backsearch = 1
        @searchback()
      return

    if txt and txt[0] != '.'
      # Completion available, complet
      if @to_complete == null
        @ws.send 'Complete', txt
        # Marking it with false -> waiting for suggest
        @to_complete = false
      else
        # Queuing completion for next suggest
        @to_complete = txt

  inspect: (e) ->
    @ws.send 'Inspect', $(e.currentTarget).attr('href')
    @working()
    false

  short_open: (e) ->
    $(e.currentTarget)
      .addClass('open')
      .removeClass('close')
      .next('.long')
      .show('fast')

  short_close: (e) ->
    $(e.currentTarget)
      .addClass('close')
      .removeClass('open')
      .next('.long')
      .hide('fast')

  toggle_visibility: (e) ->
    $(e.currentTarget)
      .add($(e.currentTarget).next())
      .toggleClass('closed', 'shown')

  unwatch: (e) ->
    @ws.send 'Unwatch', $(e.currentTarget).closest('.watching').attr 'data-expr'
    @working()

  paste_target: (e) ->
    return unless e.which == 2 # Middle
    target = $(e.target).text().trim()
    @historize target
    @ws.send 'Dump', target
    @working()
    false

  disable: ->
    @ws.send 'Disable'

  shell: ->
    @$traceback.addClass('hidden')
    @$source.find('#source-editor').addClass('hidden')
    @done()


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
