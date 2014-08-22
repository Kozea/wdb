from wdb import trace


def catched_exception(below):
    try:
        return below / 0
    except ZeroDivisionError:
        return 2


def uncatched_exception(below):
    return below / 0


def uninteresting_function(below):
    b = catched_exception(below)
    return b


def uninteresting_function_not_catching(below):
    b = uncatched_exception(below)
    return b


def uninteresting_function_catching(below):
    try:
        b = uncatched_exception(below)
    except ZeroDivisionError:
        b = 2
    return b


def one_more_step(fun, below):
    return fun(below)


# This should not stop
with trace(under=uninteresting_function):
    try:
        raise Exception('Catched Exception')
    except Exception:
        pass

# This should not stop
with trace(under=uninteresting_function):
    uninteresting_function(1)

# This should stop
# below = 1 the exception in catched exception should stop trace
with trace(under=uninteresting_function_not_catching):
    try:
        uninteresting_function_not_catching(1)
    except:
        pass

# This should stop
# below = 1 the function 2 layer under raised an exception
with trace(under=uninteresting_function_catching):
    uninteresting_function_catching(1)


# This should not stop
with trace(under=uninteresting_function):
    one_more_step(uninteresting_function, 2)

# This should stop
with trace(under=uninteresting_function_not_catching):
    try:
        one_more_step(uninteresting_function_not_catching, 2)
    except:
        pass

# This should stop
with trace(under=uninteresting_function_catching):
    one_more_step(uninteresting_function_catching, 2)
