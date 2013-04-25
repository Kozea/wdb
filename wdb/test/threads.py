# This is not currently working
from threading import Thread
from time import sleep


class Thread1(Thread):

    def run(self):
        print 'Thread 1 start'
        sleep(1)
        import wdb; wdb.set_trace()
        print 'Thread 1 end'


class Thread2(Thread):

    def run(self):
        print 'Thread 2 start'
        sleep(2)
        import wdb; wdb.set_trace()
        print 'Thread 2 end'

t1 = Thread1()
t2 = Thread2()
print 'Starting threads'
t1.start()
t2.start()

print 'Joining'
t1.join()
t2.join()

print 'The End'
