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

class Source extends Log
  constructor: (@wdb) ->
    super()
    @$container = $('.source')
      .on 'mousedown', (e) =>
        return unless e.which == 2 and @code_mirror.getOption 'readOnly'
        @code_mirror.setOption 'readOnly', 'nocursor'
      .on 'mouseup', (e) =>
        return unless e.which == 2 # Middle
        @code_mirror.setOption 'readOnly', true
        @wdb.paste_target(e)

    @code_mirror = CodeMirror (elt) =>
      @$code_mirror = $ elt
      @$container.prepend(elt)
    ,
      value: 'No active file',
      theme: 'material',
      readOnly: true,
      gutters: ['breaks', 'CodeMirror-linenumbers'],
      lineNumbers: true
      extraKeys:
        Esc: @stop_edition.bind @
        'Ctrl-S': @save.bind @

    @code_mirror.on 'gutterClick', @gutter_click.bind(@)
    $(window).on 'resize', @size.bind @
    @state =
      fn: null
      file: null
      fun: null
      lno: 0

    @fun_scope = null
    # File -> footsteps
    @footsteps = {}
    @breakpoints = {}

  external: (full=true) ->
    cursor = @code_mirror.getCursor()
    fn = "#{@state.fn}"
    if full
      fn = "#{fn}:#{cursor.line+1}:#{cursor.ch+1}"
    @wdb.ws.send 'External', fn

  save: ->
    return if @code_mirror.getOption 'readOnly'
    new_file = @code_mirror.getValue()
    @wdb.ws.send 'Save', "#{@state.fn}|#{new_file}"
    @state.file = new_file

  gutter_click: (_, n) ->
    @wdb.toggle_break ":#{n + 1}"

  clear_breakpoint: (brk) ->
    @breakpoints[brk.fn] ?= []
    if brk in @breakpoints[brk.fn]
      @breakpoints[brk.fn].splice @breakpoints[brk.fn].indexOf(brk)

    if brk.lno
      @remove_mark brk.lno
      @remove_class brk.lno, 'ask-breakpoint'
      @remove_class brk.lno, 'breakpoint'

  ask_breakpoint: (lno) ->
    @add_class lno, 'ask-breakpoint'

  set_breakpoint: (brk) ->
    @breakpoints[brk.fn] ?= []
    @breakpoints[brk.fn].push brk
    @mark_breakpoint brk

  mark_breakpoint: (brk) ->
    if brk.lno
      @remove_class brk.lno, 'ask-breakpoint'
      @add_class brk.lno, 'breakpoint'
      @add_mark brk.lno, 'breakpoint', 'breaks',
        (if brk.temporary then '○' else '●'),
         @brk_to_str brk

  brk_to_str: (brk) ->
    if brk.temporary
      str = 'Temporary '
    else
      str = ''

    str += 'Breakpoint'

    if brk.fun
      str += " On #{brk.fun}"

    if brk.lno
      str += " At #{brk.lno}"

    if brk.cond
      str += " If #{brk.cond}"

    str

  get_selection: ->
    @code_mirror.getSelection().trim()

  get_breakpoint: (n) ->
    @breakpoints[@state.fn] ?= []
    for brk in @breakpoints[@state.fn]
      if brk.lno is n
        return brk

  add_class: (lno, cls) ->
    @code_mirror.addLineClass(lno - 1, 'background', cls)

  remove_class: (lno, cls) ->
    @code_mirror.removeLineClass(lno - 1, 'background', cls)

  add_mark: (lno, cls, id, char, title) ->
    @code_mirror.setGutterMarker(lno - 1, id,
      $('<div>', class: cls, title: title).html(char).get(0))

  remove_mark: (lno) ->
    @code_mirror.setGutterMarker(lno - 1, 'breaks', null)

  stop_edition: ->
    unless @code_mirror.getOption 'readOnly'
      @toggle_edition()

  toggle_edition: ->
    was_ro = @code_mirror.getOption 'readOnly'
    @code_mirror.setOption 'readOnly', not was_ro
    @$code_mirror.toggleClass 'rw', 'ro'

    @wdb.print
      for: "Toggling edition"
      result: "Edit mode #{if was_ro then 'on' else 'off'}"

    unless was_ro
      @code_mirror.setValue @state.file

  open: (data, frame) ->
    new_state =
      fn: data.name
      file: data.file or frame.code
      fun: frame.function
      lno: frame.lno
      flno: frame.flno
      llno: frame.llno
    @set_state new_state

  set_state: (new_state) ->
    rescope = true

    if @state.fn isnt new_state.fn or @state.file isnt new_state.file
      @code_mirror.setOption('mode', @get_mode(new_state.fn))
      @code_mirror.setValue new_state.file
      for brk in @breakpoints[new_state.fn] or []
        @mark_breakpoint brk

    else
      if @state.fun isnt new_state.fun
        if @state.fun isnt '<module>'
          @remove_class @state.flno, 'ctx-top'
          for lno in [@state.flno..@state.llno]
            @remove_class lno, 'ctx'
          @remove_class @state.llno, 'ctx-bottom'
      else
        rescope = false

    @state = new_state

    @code_mirror.clearGutter 'CodeMirror-linenumbers'
    for step in @footsteps[@state.fn] or []
      @remove_class(step, 'highlighted')
      @add_class(step, 'footstep')

    if rescope and @state.fun isnt '<module>'
      @add_class @state.flno, 'ctx-top'
      for lno in [@state.flno..@state.llno]
        @add_class lno, 'ctx'
      @add_class @state.llno, 'ctx-bottom'

    @add_class(@state.lno, 'highlighted')
    @add_mark(@state.lno, 'highlighted', 'CodeMirror-linenumbers', '➤')
    @footsteps[@state.fn] ?= []
    @footsteps[@state.fn].push @state.lno

    @code_mirror.scrollIntoView
      line: @state.lno
      ch: 1,
      @$code_mirror.height() / 2
    @code_mirror.refresh()

  get_mode: (fn) ->
    switch fn.split('.').splice(-1)[0]
      when 'py'
        'python'
      when 'jinja2'
        'jinja2'
      when 'diff'
        'diff'
      else
        'python'

  focused: ->
    @$code_mirror.hasClass 'CodeMirror-focused'

  size: ->
    @$code_mirror.height 0
    @$code_mirror.height @$container.height()
    @code_mirror.refresh()
