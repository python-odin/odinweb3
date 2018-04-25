import enum

from http import HTTPStatus
from typing import Tuple


class Method(enum.Enum):
    """
    OpenAPI defined methods.
    """
    Get = 'get'
    Put = 'put'
    Post = 'post'
    Delete = 'delete'
    Options = 'options'
    Head = 'head'
    Patch = 'patch'
    Trace = 'trace'
    # Backwards compatibility with OdinWeb
    GET = 'get'
    PUT = 'put'
    POST = 'post'
    DELETE = 'delete'
    OPTIONS = 'options'
    HEAD = 'head'
    PATCH = 'patch'
    TRACE = 'trace'


# Keep HTTPStatus available for backwards compatibility, but favour Status
Status = HTTPStatus


class Location(enum.Enum):
    """
    Location where a parameter is defined for.
    """
    Path = 'path'
    Query = 'query'
    Header = 'header'
    Cookie = 'cookie'


class Style(enum.Enum):
    """
    Parameter specification style
    """
    def __new__(cls, value: str, locations: Tuple[Location, ...]) -> 'Style':
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.locations = locations
        return obj

    Matrix = 'matrix', (Location.Path,)
    Label = 'label', (Location.Path,)
    Form = 'form', (Location.Query, Location.Cookie)
    Simple = 'simple', (Location.Path, Location.Header)
    SpaceDelimited = 'spaceDelimited', (Location.Query,)
    PipeDelimited = 'pipeDelimited', (Location.Query,)
    DeepObject = 'deepObject', (Location.Query,)


class DataType(enum.Enum):
    """
    Types defined by OpenAPI Spec
    """
    Integer = 'integer', int
    Number = 'number', float
    String = 'string', str
    Boolean = 'boolean', bool
    Array = 'array', list
    Object = 'object', dict
