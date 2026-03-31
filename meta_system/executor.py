"""Parallel task execution utilities."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Iterable, List, TypeVar

T = TypeVar("T")
R = TypeVar("R")


class Executor:
    def __init__(self, max_workers: int | None = None) -> None:
        self.max_workers = max_workers

    def map_parallel(self, fn: Callable[[T], R], items: Iterable[T]) -> List[R]:
        items_list = list(items)
        if not items_list:
            return []
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = [pool.submit(fn, item) for item in items_list]
            return [future.result() for future in as_completed(futures)]
