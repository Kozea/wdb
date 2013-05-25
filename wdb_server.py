#!/usr/bin/env python
from multiprocessing import Process
from wdb.server import server, connection, child_connection, ioloop
import sys


server.listen(2560)


def run(conn):
    from wdb import Wdb
    import sys
    pyfile =  sys.argv[1]
    del sys.argv[0]
    Wdb.connection = conn
    Wdb.run_file(pyfile)


p = Process(target=run, args=(child_connection,))
p.start()

def die():
    connection.close()
    child_connection.close()
    sys.exit(0)

def poll_child():
    if p.is_alive():
        ioloop.add_callback(poll_child)
    else:
        child_connection.send('Die')
        ioloop.add_callback(die)

ioloop.add_callback(poll_child)
ioloop.start()
