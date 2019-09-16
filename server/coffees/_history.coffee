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

class History extends Log
  constructor: (@prompt) ->
    super()
    @index = -1
    @current = ''
    @currentPos = CodeMirror.Pos(0, 0)

    @oldIndex = null
    @originalIndex = null
    @overlay = null

    try
      @history = JSON.parse(localStorage['history'] or '[]')
    catch e
      @fail e
      @history = []

    @sessionIndexStart = @history.filter((e) -> e.indexOf('.') != 0).length

  up: ->
    @saveCurrent() if @index is -1

    @index = Math.min(@history.length - 1, @index + 1)
    @sync()

  down: ->
    @index = Math.max(@index - 1, -1)
    @sync()

  saveCurrent: ->
    @current = @prompt.get()
    @currentPos = @prompt.code_mirror.getCursor()

  sync: ->
    if @index is -1
      @prompt.set @current
      @prompt.code_mirror.setCursor @currentPos
    else
      @prompt.set @history[@index]
      @prompt.code_mirror.setCursor @prompt.code_mirror.lineCount(), 0

  historize: (snippet) ->
    return unless snippet
    while (index = @history.indexOf(snippet)) != -1
      @history.splice(index, 1)
    @history.unshift snippet
    localStorage and localStorage['history'] = JSON.stringify @history

  reset: ->
    @index = -1
    @current = ''
    @currentPos = CodeMirror.Pos(0, 0)

  clear: ->
    @history = []
    @sessionIndexStart = 0
    @reset()

  getOverlay: (re) ->
    token: (stream) ->
      re.lastIndex = stream.pos
      match = re.exec(stream.string)
      if match and match.index is stream.pos
        stream.pos += match[0].length or 1
        return "searching"
      else if match
        stream.pos = match.index
      else
        stream.skipToEnd()
      return

  searchPrev: (val) ->
    @searchNext val, -1

  searchNext: (val, step=1) ->
    unless @oldIndex?
      @oldIndex = @index
    unless @originalIndex?
      @originalIndex = @index
      if @index is -1
        @saveCurrent()

    while step is 1 and @index < @history.length or step is -1 and @index > -1
      @index += step
      re = new RegExp "(#{ val.replace(
        /[\-\[\]\/\{\}\(\)\*\+\?\.\\\^\$\|]/g, "\\$&") })", 'gi'
      if re.test @history[@index]
        @lastResult = @index
        @sync()
        @overlay? and @prompt.code_mirror.removeOverlay @overlay, true
        @overlay = @getOverlay re
        @prompt.code_mirror.addOverlay @overlay
        return true
    return false

  commitSearch: ->
    @oldIndex = null
    @originalIndex = null
    @index = @lastResult
    @sync()

  rollbackSearch: ->
    @oldIndex = null
    if @originalIndex?
      @index = @originalIndex
    @originalIndex = null
    @overlay? and @prompt.code_mirror.removeOverlay @overlay, true
    @overlay = null
    @sync()

  resetSearch: ->
    if @oldIndex?
      @index = @oldIndex
    @oldIndex = null

  getSessionHistory: ->
    @history.slice 0, @history.length - @sessionIndexStart

  getHistory: (direction) ->
    begin = 0
    end = @history.length - @sessionIndexStart
    if direction is 'down'
      end = @index + 1
    else if direction is 'up'
      begin = @index
    @history.slice begin, end
