a = {
    'a': 3,
}
b = {
    'b': 4,
    'a': a
}
a['b'] = b

import wdb
wdb.set_trace()
