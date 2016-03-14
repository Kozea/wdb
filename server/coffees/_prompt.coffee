
class Codemirror extends Log
  constructor: (@wdb) ->
    super
    @$container = $('#prompt')
    @code_mirror = CodeMirror (elt) =>
      @$code_mirror = $ elt
      @$container.prepend(elt)
    ,
      value: '',
      theme: 'material',
      language: 'python'
