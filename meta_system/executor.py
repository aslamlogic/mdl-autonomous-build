from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Iterable, List


class Executor:
    def __init__(self, max_workers: int | None = None) -> None:
        self.max_workers = max_workers

    def run_parallel(self, items: Iterable[Any], fn: Callable[[Any], Any]) -> List[Any]:
        items_list = list(items)
        if not items_list:
            return []
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = [pool.submit(fn, item) for item in items_list]
            results: List[Any] = []
            for future in as_completed(futures):
                results.append(future.result())
        return results
