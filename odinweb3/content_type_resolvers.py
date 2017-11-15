"""
Content Type Resolves
~~~~~~~~~~~~~~~~~~~~~

Collection of methods for resolving the content type of a request.

"""
from .bases import HttpRequestBase
from .typing import StringResolver


def accepts_header() -> StringResolver:
    """
    Resolve content type from the accepts header.
    """
    def resolver(request: HttpRequestBase):
        return request.headers.get('accepts')
    return resolver


def content_type_header() -> StringResolver:
    """
    Resolve content type from the content-type header.
    """
    def resolver(request: HttpRequestBase):
        return request.headers.get('content-type')
    return resolver


def specific_default(content_type: str) -> StringResolver:
    """
    Specify a specific default content type.
    
    :param content_type: The content type to use.

    """
    def resolver(_):
        return content_type
    return resolver
