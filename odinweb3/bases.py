"""
Base classes to be populated by
"""
from abc import ABCMeta, abstractmethod
from typing import AnyStr

from odin.bases import Codec

from .constants import Method
from .typing import StringMap, OpenApiAny, OpenApiObject
from .utils import dict_filter


class HttpRequestBase(metaclass=ABCMeta):
    """
    Base class for implementation specific HTTP Request objects
    """
    __slots__ = ('_request_codec', '_response_codec', '_current_operation')

    def __init__(self):
        self._current_operation = None
        self._request_codec = None
        self._response_codec = None

    @property
    @abstractmethod
    def scheme(self) -> str:
        """
        Request Scheme
        """

    @property
    @abstractmethod
    def host(self) -> str:
        """
        Request Host
        """

    @property
    @abstractmethod
    def method(self) -> Method:
        """
        HTTP Body
        """

    @property
    @abstractmethod
    def path(self) -> str:
        """
        Request Path
        """

    @property
    @abstractmethod
    def query(self) -> StringMap:
        """
        HTTP query arguments
        """

    @property
    @abstractmethod
    def headers(self) -> StringMap:
        """
        HTTP headers
        """

    @property
    @abstractmethod
    def cookies(self) -> StringMap:
        """
        HTTP cookies
        """

    @property
    @abstractmethod
    def post(self) -> StringMap:
        """
        HTTP post arguments
        """

    @property
    @abstractmethod
    def body(self) -> AnyStr:
        """
        HTTP Body
        """

    @property
    def current_operation(self) -> 'Operation':
        """
        The operation the current request maps to.
        """
        return self._current_operation

    @current_operation.setter
    def current_operation(self, operation: 'Operation') -> None:
        self._current_operation = operation

    @property
    def request_codec(self) -> Codec:
        """
        Codec for parsing request body.
        """
        return self._request_codec

    @request_codec.setter
    def request_codec(self, codec: Codec) -> None:
        self._request_codec = codec
        # If the response codec is un-set assume request is the response
        if self._response_codec is None:
            self._response_codec = codec

    @property
    def response_codec(self) -> Codec:
        """
        Codec for generating response body.
        """
        return self._response_codec

    @response_codec.setter
    def response_codec(self, codec: Codec) -> None:
        self._response_codec = codec


class SpecificationExtendable:
    """
    Base class for OpenAPI elements that support specification extensions.

    See: `https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.1.md#specificationExtensions`_

    To proxy values use a property eg::

        >>> class ExtendedObject(SpecificationExtendable):
        ...     @property
        ...     def my_extension(self) -> str:
        ...         return self['my_extension']

    """
    __slots__ = ('_extensions',)

    def __init__(self) -> None:
        self._extensions = {}

    def __getitem__(self, field: str) -> OpenApiAny:
        """
        Get an extension value.
        """
        return self._extensions[field]

    def __setitem__(self, field: str, value: OpenApiAny) -> None:
        """
        Set an extension value.
        """
        self._extensions[field] = value

    def to_openapi(self) -> OpenApiObject:
        """
        Output OpenAPI specification values.
        """
        return dict_filter({'x-' + f: v for f, v in self._extensions.items()})
