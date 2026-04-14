import functools
import time
import logging

from .logging import get_logger

perf_logger = get_logger("performance")


def timed(label: str = None):
    """Decorator to measure function execution duration."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000.0
            name = label or func.__name__
            perf_logger.debug(f"{name} executed in {elapsed:.3f} ms")
            return result

        return wrapper

    return decorator
