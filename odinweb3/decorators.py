from typing import Callable, Union, List

from .constants import Method

PathTypes = Union[str]


def operation(path: PathTypes, method: Method=Method.Get, operation_id: str=None,
              summary: str=None, tags: List[str]=None) -> Callable:
    """
    Decorator for defining an API operation. Usually one of the helpers (listing, detail, update, delete) would be
    used in place of this Operation decorator.
    """
    def inner(callback):
        return Operation(callback, path, method, operation_id, summary, tags)
    return inner


