if !String::startsWith
  String::startsWith = (searchString, position) ->
    position = position or 0
    @substr(position, searchString.length) == searchString

unless document.createElement('dialog').showModal
  $ ->
    $('head').append $('<script>', src: 'https://cdnjs.cloudflare.com/' +
      'ajax/libs/dialog-polyfill/0.4.3/dialog-polyfill.min.js')
    $('head').append $('<link>', rel: 'stylesheet', href: 'https://' +
      'cdnjs.cloudflare.com/ajax/libs/dialog-polyfill/0.4.3/' +
      'dialog-polyfill.min.css')
