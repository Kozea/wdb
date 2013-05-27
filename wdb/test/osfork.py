import os

print('Forking')

pid = os.fork()

if pid == 0:
    print('In children')
    import wdb; wdb.set_trace()
    print('Children dead')
else:
    print('In parent')
    import wdb; wdb.set_trace()
    print('Parent dead')

print('The End')
