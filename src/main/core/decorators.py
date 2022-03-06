import asyncio
import functools


# Stolen from stella
# https://github.com/InterStella0/stella_bot/blob/master/utils/decorators.py#L70-L79
def in_executor(loop=None):
    """Makes a sync blocking function unblocking"""
    loop = loop or asyncio.get_event_loop()

    def inner_function(func):
        @functools.wraps(func)
        def function(*args, **kwargs):
            partial = functools.partial(func, *args, **kwargs)
            return loop.run_in_executor(None, partial)

        return function

    return inner_function
