module.exports = (grunt) ->

  grunt.initConfig
    pkg: grunt.file.readJSON('package.json')

    uglify:
      options:
        banner: '/*! <%= pkg.name %>
           <%= grunt.template.today("yyyy-mm-dd") %> */\n'
        sourceMap: true

      wdb:
        files:
          'wdb_server/static/wdb.min.js': 'wdb_server/static/javascripts/wdb.js'

      deps:
        files:
          'wdb_server/static/deps.min.js': [
            'bower_components/jquery/dist/jquery.min.js'
            'bower_components/jquery-autosize/jquery.autosize.min.js'
            'bower_components/codemirror/lib/codemirror.js'
            'bower_components/codemirror/addon/runmode/runmode.js'
            'bower_components/codemirror/addon/dialog/dialog.js'
            'bower_components/codemirror/mode/python/python.js'
            'bower_components/codemirror/mode/jinja2/jinja2.js'
          ]

    cssmin:
      codemirror:
        files:
          'wdb_server/static/deps.min.css': [
            'bower_components/codemirror/lib/codemirror.css'
            'bower_components/codemirror/addon/dialog/dialog.css'
          ]

    coffee:
      options:
        sourceMap: true

      wdb:
        expand: true
        cwd: 'coffees/'
        src: '*.coffee'
        dest: 'wdb_server/static/javascripts/'
        ext: '.js'

    coffeelint:
      wdb:
        'coffees/*.coffee'

    bower:
      options:
        copy: false

      install: {}

    watch:
      files: [
        'coffees/*.coffee'
        'Gruntfile.coffee'
      ]
      tasks: ['coffeelint', 'coffee']


  grunt.loadNpmTasks 'grunt-contrib-coffee'
  grunt.loadNpmTasks 'grunt-contrib-watch'
  grunt.loadNpmTasks 'grunt-contrib-uglify'
  grunt.loadNpmTasks 'grunt-contrib-cssmin'
  grunt.loadNpmTasks 'grunt-coffeelint'
  grunt.loadNpmTasks 'grunt-sass'
  grunt.loadNpmTasks 'grunt-bower-task'

  grunt.registerTask 'dev', ['coffeelint', 'coffee', 'watch']
  grunt.registerTask 'default', [
    'coffeelint', 'coffee',
    'bower', 'uglify', 'cssmin']
