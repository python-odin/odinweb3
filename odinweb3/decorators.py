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



class Operation:
    """
    Decorator for defining an API operation. Usually one of the helpers (listing, detail, update, delete) would be
    used in place of this Operation decorator.

    Usage::

        class ItemApi(ResourceApi):
            resource = Item

            @Operation(path='', methods=Method.Get)
            def list_items(self, request):
                ...
                return items

    """
    def __new__(cls, func=None, *args, **kwargs):
        def inner(callback):
            instance = super(Operation, cls).__new__(cls)
            instance.__init__(callback, *args, **kwargs)
            return instance
        return inner(func) if func else inner

    def __init__(self, callback: Callable, path: PathTypes, ):
        pass


