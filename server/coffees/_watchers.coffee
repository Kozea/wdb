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

class Watchers extends Log
  constructor: (@wdb) ->
    super()
    @$watchers = $('.watchers')
      .on 'click', '.watching .name', @unwatch.bind @

  unwatch: (e) ->
    expr = $(e.currentTarget).closest('.watching').attr 'data-expr'
    @wdb.unwatch expr

  updateAll: (watchers) ->
    for own watcher, value of watchers
      @update(watcher, value)
    @$watchers.find('.watching:not(.updated)').remove()
    @$watchers.find('.watching').removeClass('updated')

  update: (watcher, value) ->
    $watcher = @$watchers
      .find(".watching")
      .filter((e) -> $(e).attr('data-expr') == watcher)
    if not $watcher.length
      $name = $('<code>', class: "name")
      $value = $('<div>', class: "value")
      @$watchers.append(
        $watcher = $('<div>', class: "watching")
          .attr('data-expr', watcher)
          .append($name.text(watcher), $('<code>').text(': '), $value))
      @wdb.code($value, value.toString(), [], true)
    else
      $watcher.find('.value code').remove()
      @wdb.code($watcher.find('.value'), value.toString(), [], true)
    $watcher.addClass('updated')
