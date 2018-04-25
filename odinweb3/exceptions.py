"""
Exceptions
~~~~~~~~~~

"""
from typing import Any

from .constants import Status
from .resources import Error
from .typing import StringMap


class OdinWebException(Exception):
    """
    Odin web exception.
    """


class ImmediateHttpResponse(OdinWebException):
    """
    A response that should be returned immediately.
    """
    def __init__(self, resource, status: Status=Status.OK, headers: StringMap=None):
        self.resource = resource
        self.status = status
        self.headers = headers


class HttpError(ImmediateHttpResponse):
    """
    An error response that should be returned immediately.
    """
    def __init__(self, status: Status, code_index: int=0, message: str=None, developer_message: str=None,
                 meta: Any=None, headers: StringMap=None):
        super().__init__(
            Error.from_status(status, code_index, message, developer_message, meta),
            status, headers
        )


class PermissionDenied(HttpError):
    """
    Authorization is required before making this request.
    """
    def __init__(self, message: str=None, developer_method: str=None, headers: StringMap=None):
        super().__init__(Status.UNAUTHORIZED, 0, message, developer_method, None, headers)


class AccessDenied(HttpError):
    """
    Access to the specified resource is denied.
    """
    def __init__(self, message: str=None, developer_method: str=None, headers: StringMap=None):
        super().__init__(Status.FORBIDDEN, 0, message, developer_method, None, headers)


class MultiValueDictKeyError(KeyError, OdinWebException):
    """
    Multiple value dictionary KeyError
    """
