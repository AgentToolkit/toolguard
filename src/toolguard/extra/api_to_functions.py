import inspect
from typing import Callable, List


def api_cls_to_functions(api_cls: type) -> List[Callable]:
    """Convert class methods to a list of callable functions.

    Args:
        api_cls: The class type to extract functions from.

    Returns:
        A list of public callable functions found in the class (excludes private/protected methods starting with underscore).
    """
    return [
        member
        for name, member in inspect.getmembers(api_cls, predicate=inspect.isfunction)
        if not name.startswith("_")
    ]
