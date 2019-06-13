# *-* coding: utf-8 *-*
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

import fnmatch
import os
from glob import glob
from logging import getLogger

import psutil
from tornado.ioloop import IOLoop
from tornado.options import options
from wdb_server.state import syncwebsockets

log = getLogger('wdb_server')
log.setLevel(10 if options.debug else 30)

ioloop = IOLoop.current()

try:
    import pyinotify
except ImportError:
    LibPythonWatcher = None
else:

    class LibPythonWatcher(object):
        def __init__(self, extra_search_path=None):
            inotify = pyinotify.WatchManager()
            self.files = glob('/usr/lib/libpython*')
            if not self.files:
                self.files = glob('/lib/libpython*')

            if extra_search_path is not None:
                # Handle custom installation paths
                for root, dirnames, filenames in os.walk(extra_search_path):
                    for filename in fnmatch.filter(filenames, 'libpython*'):
                        self.files.append(os.path.join(root, filename))

            log.debug('Watching for %s' % self.files)
            self.notifier = pyinotify.TornadoAsyncNotifier(
                inotify, ioloop, self.notified, pyinotify.ProcessEvent()
            )
            inotify.add_watch(
                self.files,
                pyinotify.EventsCodes.ALL_FLAGS['IN_OPEN']
                | pyinotify.EventsCodes.ALL_FLAGS['IN_CLOSE_NOWRITE'],
            )

        def notified(self, notifier):
            log.debug('Got notified for %s' % self.files)
            refresh_process()
            log.debug('Process refreshed')

        def close(self):
            log.debug('Closing for %s' % self.files)
            self.notifier.stop()


def refresh_process(uuid=None):
    if uuid is not None:
        send = lambda cmd, data: syncwebsockets.send(uuid, cmd, data)
    else:
        send = syncwebsockets.broadcast

    remaining_pids = []
    remaining_tids = []
    for proc in psutil.process_iter():
        try:
            cl = proc.cmdline()
        except (
            psutil.ZombieProcess,
            psutil.AccessDenied,
            psutil.NoSuchProcess,
        ):
            continue
        else:
            if len(cl) == 0:
                continue

        binary = cl[0].split('/')[-1]
        if (
            ('python' in binary or 'pypy' in binary)
            and proc.is_running()
            and proc.status() != psutil.STATUS_ZOMBIE
        ):
            try:
                try:
                    cpu = proc.cpu_percent(interval=0.01)
                    send(
                        'AddProcess',
                        {
                            'pid': proc.pid,
                            'user': proc.username(),
                            'cmd': ' '.join(proc.cmdline()),
                            'threads': proc.num_threads(),
                            'time': proc.create_time(),
                            'mem': proc.memory_percent(),
                            'cpu': cpu,
                        },
                    )
                    remaining_pids.append(proc.pid)
                    for thread in proc.threads():
                        send('AddThread', {'id': thread.id, 'of': proc.pid})
                        remaining_tids.append(thread.id)
                except psutil.NoSuchProcess:
                    pass
            except Exception:
                log.warn('', exc_info=True)
                continue

    send('KeepProcess', remaining_pids)
    send('KeepThreads', remaining_tids)
