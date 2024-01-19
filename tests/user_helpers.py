from time import perf_counter
from typing import Any, Callable
from functools import wraps
from typing import NamedTuple

class Result(NamedTuple):
    result: Any
    time: float

def timed(func: Callable):
    """Decorate functions that added performance timing. This is only timed the function once per-call.
    
    Returns: Result"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = perf_counter()
        result = func(*args, **kwargs)
        end = perf_counter()
        return Result(result, end-start)
    return wrapper

def timed_oncall(func: Callable, *args, **kwargs):
    """Immediately calls a function and return Result."""
    start = perf_counter()
    result = func(*args, **kwargs)
    end = perf_counter()
    return Result(result, end-start)
