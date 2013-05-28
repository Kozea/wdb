import wdb
wdb.start_trace()
a = 2
b = 4
c = a + b
print(c)
d = c / 0

print(d)
print('The end')
wdb.stop_trace()
