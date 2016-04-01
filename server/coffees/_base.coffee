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

class Log
  constructor: ->
    @debug = $('body').attr('data-debug') or false

  time: ->
    date = new Date()
    "#{date.getHours()}:#{date.getMinutes()}:" +
    "#{date.getSeconds()}.#{date.getMilliseconds()}"

  log: ->
    if @debug
      name = "[#{@constructor.name}] (#{@time()})"
      log_args = [name].concat Array.prototype.slice.call(arguments, 0)
      console.log.apply console, log_args

  dbg: ->
    if @debug
      name = "[#{@constructor.name}] (#{@time()})"
      log_args = [name].concat Array.prototype.slice.call(arguments, 0)
      console.debug.apply console, log_args

  fail: ->
    name = @constructor.name
    log_args = [name].concat Array.prototype.slice.call(arguments, 0)
    console.error.apply console, log_args
