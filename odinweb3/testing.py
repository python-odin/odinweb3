"""
Testing Helpers
~~~~~~~~~~~~~~~

Collection of Mocks and Tools for testing APIs.

"""
from collections import MutableMapping
from typing import AnyStr

from odin.codecs import json_codec
from urllib.parse import urlparse, parse_qs

from odin.utils import lazy_property

from .bases import HttpRequestBase
from .constants import Method
from .data_structures import MultiValueDict
from .typing import StringMap


class MockRequest(HttpRequestBase):
    """
    Mocked Request object.

    This can be treated as a template of a request
    """
    @classmethod
    def from_uri(cls, uri: str, post: StringMap=None, headers: StringMap=None, method: Method=Method.GET,
                 body: AnyStr='', request_codec=None, response_codec=None) -> 'MockRequest':
        scheme, netloc, path, _, query, _ = urlparse(uri)
        return cls(scheme, netloc, path, parse_qs(query), headers, method, post, body, request_codec, response_codec)

    def __init__(self, scheme: str='http', host: str='127.0.0.1', path: str=None,
                 query: MultiValueDict=None, headers: MultiValueDict=None, method: Method=Method.GET,
                 post: MultiValueDict=None, body: AnyStr='', request_codec=None, response_codec=None):
        self._scheme = scheme
        self._host = host
        self._path = path
        self._query = MultiValueDict(query or {})
        self._headers = headers or {}
        self._method = method
        self._post = MultiValueDict(post or {})
        self._body = body
        self._request_codec = request_codec or json_codec
        self._response_codec = response_codec or json_codec

    @lazy_property
    def scheme(self):
        return self._scheme

    @lazy_property
    def host(self):
        return self._host

    @lazy_property
    def path(self):
        return self._path

    @lazy_property
    def query(self):
        return self._query

    @lazy_property
    def headers(self):
        return self._headers

    @lazy_property
    def method(self):
        return self._method

    @lazy_property
    def post(self):
        return self._post

    @lazy_property
    def body(self):
        return self._body


def check_request_proxy(request_proxy):
    """
    A set of standard tests for Request Proxies.

    This is for use by integrations with python web frameworks to verify the request proxy
    behaves as expected.

    """
    for attr, expected_type in (
        ('scheme', str),
        ('host', str),
        ('path', None),
        ('query', MultiValueDict),
        ('headers', (dict, MutableMapping)),
        ('method', Method),
        ('post', MultiValueDict),
        ('body', None),
    ):
        assert hasattr(request_proxy, attr), "{} instance missing attribute {}.".format(request_proxy.__class__, attr)
        obj = getattr(request_proxy, attr)
        if expected_type:
            assert isinstance(obj, expected_type), "Incorrect type of {}.{}; expected {} got {}.".format(
                request_proxy.__class__, attr, expected_type, type(obj))
