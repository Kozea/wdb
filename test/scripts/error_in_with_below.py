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
# below = 1 so in trace exception should be ignored
with trace(below=1):
    try:
        raise Exception('Catched Exception')
    except Exception:
        pass

# This should not stop
# below = 1 so catched function 2 layer under are ignored
with trace(below=1):
    uninteresting_function(1)

# This should stop
# below = 1 the exception in catched exception should stop trace
with trace(below=1):
    try:
        uninteresting_function_not_catching(1)
    except:
        pass

# This should stop
# below = 1 the function 2 layer under raised an exception
with trace(below=1):
    uninteresting_function_catching(1)


# This should not stop neither
with trace(below=2):
    try:
        raise Exception('Catched Exception')
    except Exception:
        pass

# This should not stop
with trace(below=2):
    one_more_step(uninteresting_function, 2)

# This should stop
with trace(below=2):
    try:
        one_more_step(uninteresting_function_not_catching, 2)
    except:
        pass

# This should stop
with trace(below=2):
    one_more_step(uninteresting_function_catching, 2)
