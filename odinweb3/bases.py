from abc import ABCMeta, abstractmethod
from typing import AnyStr

from .constants import Method
from .typing import StringMap


class HttpRequestBase(metaclass=ABCMeta):
    """
    Base class for implementation specific HTTP Request objects
    """
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
        HTTP header arguments
        """

    @property
    @abstractmethod
    def method(self) -> Method:
        """
        HTTP Body
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
    def request_codec(self):
        """
        Codec for parsing
        """

    @property
    def response_codec(self):
        """
        HTTP Body
        """
