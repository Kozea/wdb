#!/usr/bin/env python
from multiprocessing import Process
from wdb.server import server, connection, child_connection, WebSocketHandler
import tornado.ioloop
import sys

ioloop = tornado.ioloop.IOLoop.instance()
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
        for client in WebSocketHandler.clients.values():
            client.write_message('Die')
        ioloop.add_callback(die)


def transmit():
    try:
        poll = connection.poll()
    except:
        return

    if poll:
        message = connection.recv()
        pipe = message.index('|')
        uuid, message = message[:pipe], message[pipe + 1:]
        try:
            WebSocketHandler.clients[uuid].write_message(message)
        except:
            return
    ioloop.add_callback(transmit)


ioloop.add_callback(poll_child)
ioloop.add_callback(transmit)
try:
    ioloop.start()
except KeyboardInterrupt:
    if p.is_alive():
        p.terminate()
