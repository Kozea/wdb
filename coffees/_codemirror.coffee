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

class Codemirror extends Log
  constructor: (@wdb) ->
    CodeMirror.keyMap.wdb =
      Esc: (cm) => @stop_edition()
      fallthrough: ["default"]

    CodeMirror.commands.save = =>
      @wdb.ws.send 'Save', "#{@fn}|#{@code_mirror.getValue()}"

    @code_mirror = null
    @$container = $('#source-editor')
    @bg_marks =
      cls: {}
      marks: {}

    @rw = false
    @fn = null
    @file = null
    @fun = null
    @last_hl = null

  new: (file, name, rw=false) ->
    @code_mirror = CodeMirror (elt) =>
      @$container.prepend(elt)
      $(elt)
        .addClass(if rw then 'rw' else 'ro')
        .addClass('cm')
    ,
      value: file,
      mode:  @get_mode(name),
      readOnly: !rw,
      theme: 'wdb',
      keyMap: 'wdb',
      gutters: ["breakpoints", "CodeMirror-linenumbers"],
      lineNumbers: true

    @code_mirror.on 'gutterClick', @gutter_click.bind(@)

    @rw = rw
    @fn = name
    @file = file
    @fun = null
    @last_hl = null

  gutter_click: (_, n) ->
    @wdb.toggle_break ':' + (n + 1)

  clear_breakpoint: (lno) ->
    @remove_mark(lno)
    @remove_class(lno, 'breakpoint')

  ask_breakpoint: (lno) ->
    @add_class(lno, 'ask-breakpoint')

  get_selection: ->
    @code_mirror.getSelection().trim()

  has_breakpoint: (n) ->
    line_cls = @code_mirror.lineInfo(n - 1).bgClass
    return false unless line_cls
    return 'breakpoint' in line_cls.split(' ')

  add_class: (lno, cls) ->
    @code_mirror.addLineClass(lno - 1, 'background', cls)
    if @bg_marks.cls[lno]
      @bg_marks.cls[lno] = @bg_marks.cls[lno] + ' ' + cls
    else
      @bg_marks.cls[lno] = cls

  remove_class: (lno, cls) ->
    @code_mirror.removeLineClass(lno - 1, 'background', cls)
    delete @bg_marks.cls[lno]

  add_mark: (lno, cls, char) ->
    @bg_marks.marks[lno] = [cls, char]
    @code_mirror.setGutterMarker(lno - 1, "breakpoints",
      $('<div>', class: cls).html(char).get(0))

  remove_mark: (lno) ->
    delete @bg_marks.marks[lno]
    @code_mirror.setGutterMarker(lno - 1, "breakpoints", null)

  stop_edition: ->
    @toggle_edition() if @rw

  toggle_edition: ->
    @rw = not @rw
    cls = $.extend({}, @bg_marks.cls)
    marks = $.extend({}, @bg_marks.marks)
    scroll = $('#source .CodeMirror-scroll').scrollTop()
    $('#source .CodeMirror').remove()
    @code_mirror = @new @file, @fn, rw
    for lno of cls
      @add_class(lno, cls[lno])
    for lno of marks
      [cls, char] = marks[lno]
      @add_mark(lno, cls, char)
    $('#source .CodeMirror-scroll').scrollTop(scroll)
    @print
      for: "Toggling edition"
      result: "Edit mode #{if rw then 'on' else 'off'}"

  open: (data, frame) ->
    if not @code_mirror
      @new data.file, data.name
      @wdb.$eval.focus()
    else
      if @fn == data.name
        if @fun != frame.function
          for lno of @bg_marks.cls
            @code_mirror.removeLineClass(lno - 1, 'background')

        for lno of @bg_marks.marks
          @code_mirror.setGutterMarker(lno - 1, 'breakpoints', null)
        if @last_hl
          @code_mirror.removeLineClass(lno - 1, 'background')
          @code_mirror.addLineClass(lno - 1, 'background', 'footstep')
      else
        @code_mirror.setValue data.file
        @fn = data.name
        @fun = frame.function
        @file = data.file
        @last_hl = null
      @bg_marks.cls = {}
      @bg_marks.marks = {}

    for lno in data.breaks
      @add_class(lno, 'breakpoint')
      @add_mark(lno, 'breakpoint', '●')

    @add_class(frame.lno, 'highlighted')
    @add_mark(frame.lno, 'highlighted', '➤')
    if @fun != frame.function and
       frame.function != '<module>'
      for lno in [frame.flno...frame.llno + 1]
        @add_class(lno, 'ctx')
        if lno == frame.flno
          @add_class(lno, 'ctx-top')
        else if lno == frame.llno
          @add_class(lno, 'ctx-bottom')
      @fun = frame.function
    @last_hl = frame.lno

    @code_mirror.scrollIntoView(line: frame.lno, ch: 1, 1)
    $scroll = $ '#source .CodeMirror-scroll'
    $hline = $ '#source .highlighted'
    $scroll.scrollTop(
      $hline.offset().top - $scroll.offset().top +
      $scroll.scrollTop() - $scroll.height() / 2)

  get_mode: (fn) ->
    switch fn.split('.').splice(-1)[0]
      when 'py'
        'python'
      when 'jinja2'
        'jinja2'
      else
        'python'
