import functools
from typing import Callable, List, TypeVar


def flatten(arr_arr):
    return [b for bs in arr_arr for b in bs]


def sum(array):
    return functools.reduce(lambda a, b: a + b, array) if len(array) > 0 else 0


T = TypeVar("T")


def find(array: List[T], pred: Callable[[T], bool]):
    for item in array:
        if pred(item):
            return item


# remove duplicates and preserve ordering
def remove_duplicates(array: List[T]) -> List[T]:
    res = []
    visited = set()
    for item in array:
        if item not in visited:
            res.append(item)
            visited.add(item)
    return res


def not_none(array: List[T]) -> List[T]:
    return [item for item in array if item is not None]
