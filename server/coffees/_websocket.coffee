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

class Websocket extends Log
  constructor: (@wdb, uuid) ->
    super()
    # Open a websocket in case of request break
    proto = if (document.location.protocol == "https:") then "wss:" else "ws:"
    @url = "#{proto}//#{document.location.host}/websocket/#{uuid}"
    @log 'Opening new socket', @url
    @ws = new WebSocket @url
    @ws.onclose = @close.bind(@)
    @ws.onopen = @open.bind(@)
    @ws.onerror = @error.bind(@)
    @ws.onmessage = @message.bind(@)

  close: (m) ->
    @log "Closed", m
    @wdb.die()

  error: (m) ->
    @fail "Error", m

  open: (m) ->
    # We are connected, ie: in request break
    @log "Open", m
    @wdb.opening()

  message: (m) ->
    # Open a websocket in case of request break
    message = m.data
    pipe = message.indexOf('|')
    if pipe > -1
      cmd = message.substr(0, pipe)
      data = JSON.parse message.substr(pipe + 1)
    else
      cmd = message
    @dbg @time(), '<-', message
    cmd = cmd.toLowerCase()
    if cmd of @wdb
      @wdb[cmd.toLowerCase()] data
    else
      @fail 'Unknown command', cmd

  send: (cmd, data=null) ->
    if data
      if typeof(data) isnt 'string'
        data = JSON.stringify data
      msg = "#{cmd}|#{data}"
    else
      msg = cmd
    @dbg '->', msg
    @ws.send msg
