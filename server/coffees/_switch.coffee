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

class Switch extends Log
  constructor: (@wdb) ->
    super()
    @$trace = $('.trace')
    @$switches = $('.switch').click (e) => @switch $(e.currentTarget)
    @$command = $('.command').click (e) => @command $(e.currentTarget)
    @$source = $('.source')
    @$interpreter = $('.interpreter')

  switch: ($switch)->
    if $switch.is('.power')
      if $switch.is('.off')
        @wdb.disable()
      else if $switch.is('.on')
        parent.postMessage('activate', '*')
    else if $switch.is('.code')
      if $switch.is('.off')
        @open_code()
      else if $switch.is('.on')
        @close_code()
    else if $switch.is('.term')
      if $switch.is('.off')
        @open_term()
      else if $switch.is('.on')
        @close_term()

  open_trace: ->
    @$trace.addClass('mdl-layout--fixed-drawer')

  close_trace: ->
    @$trace.removeClass('mdl-layout--fixed-drawer')

  open_code: ->
    @$switches.filter('.code').removeClass('off').addClass('on')
      .removeClass('mdl-button--accent')
    @$source.removeClass('hidden')
    @wdb.source.size()

  close_code: ->
    @$switches.filter('.code').removeClass('on').addClass('off')
      .addClass('mdl-button--accent')
    @$source.addClass('hidden')
    @wdb.source.size()

  open_term: ->
    @$switches.filter('.term').removeClass('off').addClass('on')
      .removeClass('mdl-button--accent')
    @$interpreter.removeClass('hidden')
    @wdb.source.size()

  close_term: ->
    @$switches.filter('.term').removeClass('on').addClass('off')
      .addClass('mdl-button--accent')
    @$interpreter.addClass('hidden')
    @wdb.source.size()

  command: ($command)->
    @wdb.execute '.' + $command.attr('data-command')
