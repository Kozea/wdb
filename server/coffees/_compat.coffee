if !String::startsWith
  String::startsWith = (searchString, position) ->
    position = position or 0
    @substr(position, searchString.length) == searchString
