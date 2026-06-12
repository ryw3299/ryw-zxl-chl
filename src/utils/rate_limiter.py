"""Rate limiter utilities for controlling concurrent LLM calls."""

from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from threading import Semaphore
from typing import Any, Optional, TypeVar

T = TypeVar("T")


class RateLimiter:
    """Simple semaphore-based rate limiter for controlling concurrent operations.

    Usage:
        limiter = RateLimiter(max_concurrent=5)
        with limiter:
            # Only 5 operations can run concurrently
            do_something()
    """

    def __init__(self, max_concurrent: int = 5):
        """Initialize the rate limiter.

        Args:
            max_concurrent: Maximum number of concurrent operations. Default is 5.
        """
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be at least 1")
        self._semaphore = Semaphore(max_concurrent)
        self._max_concurrent = max_concurrent

    @property
    def max_concurrent(self) -> int:
        """Return the maximum concurrent operations allowed."""
        return self._max_concurrent

    @contextmanager
    def __call__(self) -> Iterator[None]:
        """Context manager for acquiring and releasing the semaphore."""
        self._semaphore.acquire()
        try:
            yield
        finally:
            self._semaphore.release()

    @contextmanager
    def acquire(self) -> Iterator[None]:
        """Alias for __call__ for clarity."""
        with self.__call__():
            yield


def run_parallel(
    func: Callable[..., T],
    items: list[Any],
    max_workers: Optional[int] = None,
    description: str = "parallel task",
) -> list[T]:
    """Run a function on multiple items in parallel using ThreadPoolExecutor.

    Args:
        func: The function to call on each item. Should return a result.
        items: List of items to process.
        max_workers: Maximum concurrent workers. If None, defaults to 5.
        description: Description for logging (not currently used).

    Returns:
        List of results in the same order as items.

    Example:
        results = run_parallel(
            lambda x: process_item(x),
            items=[1, 2, 3],
            max_workers=5
        )
    """
    if max_workers is None:
        max_workers = 5

    if not items:
        return []

    if max_workers == 1:
        # Serial execution for single worker
        return [func(item) for item in items]

    limiter = RateLimiter(max_concurrent=max_workers)

    def _limited_call(item: Any) -> T:
        with limiter():
            return func(item)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(_limited_call, items))

    return results
