from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, Future
from typing import Any, Callable, Iterable, List


class TaskExecutor:
    def __init__(self, max_workers: int = 8) -> None:
        self.max_workers = max_workers

    def run(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return fn(*args, **kwargs)

    def map(self, fn: Callable[[Any], Any], items: Iterable[Any]) -> List[Any]:
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            return list(pool.map(fn, items))

    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Future:
        pool = ThreadPoolExecutor(max_workers=self.max_workers)
        return pool.submit(fn, *args, **kwargs)
