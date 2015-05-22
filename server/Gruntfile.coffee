module.exports = (grunt) ->
  require('time-grunt') grunt
  require('load-grunt-tasks')(grunt)
  jsdeps = [
    'bower_components/jquery/dist/jquery.min.js'
    'bower_components/jquery-autosize/jquery.autosize.min.js'
    'bower_components/codemirror/lib/codemirror.js'
    'bower_components/codemirror/addon/runmode/runmode.js'
    'bower_components/codemirror/addon/dialog/dialog.js'
    'bower_components/codemirror/mode/python/python.js'
    'bower_components/codemirror/mode/jinja2/jinja2.js'
    'bower_components/codemirror/mode/diff/diff.js'
  ]
  cssdeps = [
    'bower_components/font-awesome/css/font-awesome.min.css'
    'bower_components/codemirror/lib/codemirror.css'
    'bower_components/codemirror/addon/dialog/dialog.css'
  ]

  grunt.initConfig
    pkg: grunt.file.readJSON('package.json')
    fileExists:
      jsdeps: jsdeps
      cssdeps: cssdeps

    imageEmbed:
      options:
        maxImageSize: 0
        regexInclude: /^[^#].+$/g
        regexExclude: /^#.+$/g

      cssdeps:
        files:
          'wdb_server/static/stylesheets/deps.embed.css': cssdeps

    uglify:
      options:
        banner: '/*! <%= pkg.name %>
           <%= grunt.template.today("yyyy-mm-dd") %> */\n'

      wdb:
        expand: true
        cwd: 'wdb_server/static/javascripts'
        src: '*.js'
        dest: 'wdb_server/static/javascripts/wdb/'
        ext: '.min.js'

      deps:
        files:
          'wdb_server/static/javascripts/wdb/deps.min.js': jsdeps

    sass:
      wdb:
        expand: true
        cwd: 'sass/'
        src: '*.sass'
        dest: 'wdb_server/static/stylesheets/'
        ext: '.css'

    autoprefixer:
      hydra:
        expand: true
        cwd: 'wdb_server/static/stylesheets/'
        src: '*.css'
        dest: 'wdb_server/static/stylesheets/'

    cssmin:
      codemirror:
        files:
          'wdb_server/static/stylesheets/deps.min.css': (
            'wdb_server/static/stylesheets/deps.embed.css')

    coffee:
      options:
        bare: true
        join: true
      wdb:
        files:
          'wdb_server/static/javascripts/wdb.js': [
            'coffees/_base.coffee'
            'coffees/_websocket.coffee'
            'coffees/_codemirror.coffee'
            'coffees/wdb.coffee'
          ]

      500:
        files:
          'wdb_server/static/javascripts/500.js': [
            'coffees/_base.coffee'
            'coffees/500.coffee'
          ]

      status:
        files:
          'wdb_server/static/javascripts/status.js': [
            'coffees/_base.coffee'
            'coffees/status.coffee'
          ]


    coffeelint:
      wdb:
        'coffees/*.coffee'

    bower:
      options:
        copy: false

      install: {}

    watch:
      options:
        livereload: true

      coffee:
        files: [
          'coffees/*.coffee'
          'Gruntfile.coffee'
        ]
        tasks: ['coffeelint', 'coffee']

      sass:
        files: [
          'sass/*.sass'
        ]
        tasks: ['sass']

  grunt.loadNpmTasks 'grunt-contrib-coffee'
  grunt.loadNpmTasks 'grunt-contrib-watch'
  grunt.loadNpmTasks 'grunt-contrib-uglify'
  grunt.loadNpmTasks 'grunt-contrib-cssmin'
  grunt.loadNpmTasks 'grunt-coffeelint'
  grunt.loadNpmTasks 'grunt-autoprefixer'
  grunt.loadNpmTasks 'grunt-sass'
  grunt.loadNpmTasks 'grunt-bower-task'

  grunt.registerTask 'dev', ['coffeelint', 'coffee', 'watch']
  grunt.registerTask 'css', ['sass']
  grunt.registerTask 'default', [
    'coffeelint', 'coffee',
    'sass', 'autoprefixer',
    'bower', 'fileExists',
    'imageEmbed',
    'uglify', 'cssmin']
