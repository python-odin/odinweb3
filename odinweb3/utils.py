"""
Utils
~~~~~

Utility functions used to perform common operations.

"""
import os
import base64

from typing import Iterable, Callable


def token(bit_depth: int=64, encoder: Callable[[str], bytes]=base64.b32encode) -> str:
    """
    Generate a random token of a certain bit depth and strip any padding.
    """
    chars = bit_depth >> 3  # Divide by 8
    if bit_depth == chars << 3:
        data = os.urandom(chars)
        return encoder(data).decode().rstrip('=')
    raise ValueError("Bit depth must be a multiple of 8")


def dict_filter(*args: dict, base: dict=None) -> dict:
    """
    Merge values from multiple dictionaries into a single dictionary while
    filtering out ``None`` values.

    Use the *base* argument to provide a base dictionary (this dict will not
    be ``None`` filtered). This is to handle dictionaries that have already
    been filtered.

    """
    result = base or {}
    for arg in args:
        result.update(i for i in arg.items() if i[1] is not None)
    return result


def sort_by_priority(iterable: Iterable, reverse: bool=False, default_priority: int=10) -> list:
    """
    Return a list or objects sorted by a priority value.
    """
    return sorted(iterable, reverse=reverse, key=lambda o: getattr(o, 'priority', default_priority))
