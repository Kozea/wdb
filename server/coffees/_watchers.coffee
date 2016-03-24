class Watchers extends Log
  constructor: (@wdb) ->
    super
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
