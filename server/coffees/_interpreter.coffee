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

class Interpreter extends Log
  constructor: (@wdb) ->
    super()
    @$terminal = $('.terminal')
      .on 'click', =>
        unless getSelection().toString()
          @focus()
      .on 'click', 'a.inspect', @inspect.bind @
    @$scrollback = $('.scrollback')
      .on 'click', '.short.close', @short_open.bind @
      .on 'click', '.short.open', @short_close.bind @
      .on 'click', '.toggle', @toggle_visibility.bind @


  scroll: (direction=null)->
    if direction
      @$terminal.scrollTop(
        @$terminal.scrollTop() + direction * @$terminal.height())
      return

    @wdb.prompt.$container.get(0).scrollIntoView
      behavior: "smooth"

  clear: ->
    @$scrollback.empty()

  write: (elt) ->
    @$scrollback.append elt

  inspect: (e) ->
    @wdb.inspect $(e.currentTarget).attr('href')

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

  focus: (e) ->
    scroll = @$terminal.scrollTop()
    @wdb.prompt.focus()
    @$terminal.scrollTop scroll
