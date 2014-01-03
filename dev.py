#!/usr/bin/env python
from wsreload.client import watch
from subprocess import Popen
from glob import glob
import time
import shlex
from subprocess import call


commands = [
    'coffee ' +
    ' -wc -o wdb_server/static/javascripts/ ' +
    ' '.join(glob('wdb_server/static/coffees/*.coffee')),
    'compass watch wdb_server/static'
]


process = {}
for cmd in commands:
    print('Lauching %s' % cmd)
    process[cmd] = Popen(shlex.split(cmd))

files = ['wdb_server/static/javascripts/', 'wdb_server/static/stylesheets/',
         'wdb_server/templates/']
watch({'url': 'http://localhost:1984/*'}, files, unwatch_at_exit=True)

call(['curl', 'http://localhost:1984/self'])

try:
    while len(process):
        for cmd, proc in list(process.items()):
            if proc.poll():
                print('%s has terminated.' % cmd)
                process.pop(cmd)
        time.sleep(0.1)
    print('All children are dead. Time to go.')

except KeyboardInterrupt:
    print('\nGot [ctrl]+[c]')
    for cmd, proc in process.items():
        print('Killing %s' % cmd)
        proc.kill()
    print('Bye bye.')
