from wdb import trace


def uncatched_exception(below):
    return below / 0


def uninteresting_exception(below):
    return below.what


def uninteresting_function_catching(below):
    # Uninteresting exception
    try:
        uninteresting_exception(below)
    except AttributeError:
        pass

    try:
        b = uncatched_exception(below)
    except ZeroDivisionError:
        b = 2

    return b


def the_step_more(below):
    try:
        below.what
    except AttributeError:
        pass

    try:
        return uncatched_exception(below)
    except ZeroDivisionError:
        return 2


def uninteresting_function_catching_with_a_step_more(below):
    # Uninteresting exception
    try:
        uninteresting_exception(below)
    except AttributeError:
        pass

        b = the_step_more(below)
    return b


def one_more_step(fun, below):
    try:
        uninteresting_exception(below)
    except AttributeError:
        pass

    return fun(below)


# This should stop for both
with trace(under=uninteresting_function_catching):
    uninteresting_function_catching(0)

# This should stop only for the latter in uncatched
with trace(under=uncatched_exception):
    uninteresting_function_catching(0)

# This should not stop
with trace(under=the_step_more):
    uninteresting_function_catching(0)

# This should not stop
with trace(under=uncatched_exception, below=1):
    uninteresting_function_catching(0)

# This should stop in uncatched_exception
with trace(under=the_step_more, below=1):
    uninteresting_function_catching_with_a_step_more(1)

# This should stop in uncatched_exception
with trace(under=the_step_more, below=1):
    one_more_step(uninteresting_function_catching_with_a_step_more, 2)
