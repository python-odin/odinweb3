"""
Resources
~~~~~~~~~

Common resources for use in APIs.

"""
import odin

from .constants import Status
from .typing import OpenApiAny


class Error(odin.Resource):
    """
    Response returned for errors.

    The *meta* field should be utilised to provide additional information that
    is specific to the error, eg if validation field then meta would contain
    an object that maps field names to error messages.

    """
    class Meta:
        namespace = None

    @classmethod
    def from_status(cls, status: Status, code_index: int=0, message: str=None,
                    developer_message: str=None, meta: OpenApiAny=None) -> 'Error':
        """
        Automatically build an HTTP response from the HTTP Status code.
        
        :param status:
        :param code_index: 
        :param message: 
        :param developer_message: 
        :param meta: 

        """
        return cls(
            status.value,
            (status.value * 100) + code_index,
            message or status.description,
            developer_message or status.description,
            meta
        )

    status = odin.Integer(
        help_text="HTTP status code of the response."
    )
    code = odin.Integer(
        help_text="Custom application specific error code that references into "
                  "the application."
    )
    message = odin.String(
        help_text="A message that can be displayed to an end user"
    )
    developer_message = odin.String(
        null=True,
        help_text="An error message suitable for the application developer"
    )
    meta = odin.AnyValue(
        null=True,
        help_text="Additional meta information that can help solve errors."
    )
