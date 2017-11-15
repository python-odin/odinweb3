"""
Utils
~~~~~

Utility functions used to perform common operations.

"""
import os
import base64
import itertools

from typing import Any, Iterable


def token(bit_depth: int=64, encoder=base64.b32encode) -> str:
    """
    Generate a random token of a certain bit depth and strip any padding.
    """
    chars = bit_depth >> 3  # Divide by 8
    if bit_depth == chars << 3:
        data = os.urandom(chars)
        return encoder(data).decode().rstrip('=')
    raise ValueError("Bit depth must be a multiple of 8")


def to_bool(value: Any) -> bool:
    """
    Convert a value into a bool but handle "truthy" strings eg, yes, true, ok, y
    """
    if isinstance(value, str):
        return value.upper() in ('Y', 'YES', 'T', 'TRUE', '1', 'OK')
    return bool(value)


def dict_filter_update(base: dict, updates: dict):
    """
    Update dict with None values filtered out.
    """
    base.update((k, v) for k, v in updates.items() if v is not None)


def dict_filter(*args: dict, **kwargs) -> dict:
    """
    Merge all values into a single dict with all None values removed.
    """
    result = {}
    for arg in itertools.chain(args, (kwargs,)):
        dict_filter_update(result, arg)
    return result


def sort_by_priority(iterable: Iterable, reverse: bool=False, default_priority: int=10):
    """
    Return a list or objects sorted by a priority value.
    """
    return sorted(iterable, reverse=reverse, key=lambda o: getattr(o, 'priority', default_priority))
