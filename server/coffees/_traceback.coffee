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

class Traceback extends Log
  constructor: (@wdb) ->
    super()
    @$traceback = $('.traceback')
    @$traceback.on 'click', '.trace-line', @select.bind @

  select: (e) ->
    level = $(e.currentTarget).attr('data-level')
    @wdb.select_trace level
    # Yeah...
    if $('.mdl-layout__obfuscator').is '.is-visible'
      $('.mdl-layout').get(0).MaterialLayout.toggleDrawer()
    false

  make_trace: (trace) ->
    @clear()
    @show()
    for frame in trace
      $traceline = $('<a>',
        class:'trace-line ellipsis
        mdl-list__item mdl-list__item--three-line trace-' + frame.level)
        .attr('data-level', frame.level)
        .attr('title',
          "File \"#{frame.file}\", line #{frame.lno}, in #{frame.function}\n" +
          "    #{frame.code}")

      for brk in @wdb.source.breakpoints[frame.file] or []
        unless brk.cond or brk.fun or brk.lno
          $traceline.addClass('breakpoint')
          break

      if frame.current
        $traceline.addClass('real-selected')

      $primary = $('<div>', class: 'mdl-list__item-primary-content')
      $primary.append $('<div>', class: 'ellipsis').text(frame.function)

      $primary
        .append($('<div>', class: 'mdl-list__item-text-body')
          .append $tracebody = $('<div>', class: 'ellipsis')
          .append $('<div>', class: 'ellipsis').text(
            frame.file.split('/').slice(-1)[0] + ':' + frame.lno).prepend(
              $('<i>', class: 'material-icons').text(@get_fn_icon(frame.file)))
      )

      @wdb.code $tracebody, frame.code, ['ellipsis']

      $traceline.append $primary
      @$traceback.prepend $traceline

  hide: ->
    @$traceback.addClass('hidden')

  show: ->
    @$traceback.removeClass('hidden')

  clear: ->
    @$traceback.empty()

  get_fn_icon: (fn) ->
    # TODO: other platforms
    if !!~ fn.indexOf('site-packages')
      'library_books'
    else if fn.startsWith(@wdb.cwd) or fn[0] isnt '/'
      'star'
    else if fn.startsWith '/home/'
      'home'
    else if fn.startsWith('/usr/lib') and !!~ fn.indexOf('/python')
      'lock'
    else
      'cloud'
