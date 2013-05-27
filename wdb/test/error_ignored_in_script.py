import wdb
wdb.start_trace()
a = 2
b = 4
c = a + b
print(c)
wdb.stop_trace()
d = c / 0

print(d)
print('The end')
