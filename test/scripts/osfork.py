import os
from wdb import set_trace as wtf


print('Forking')

pid = os.fork()

if pid == 0:
    print('In children')
    wtf()
    print('Children dead')
else:
    print('In parent')
    wtf()
    print('Parent dead')

print('The End')
