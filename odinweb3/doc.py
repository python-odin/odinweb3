from .bases import SpecificationExtendable
from .typing import OpenApiAny, OpenApiObject
from .utils import dict_filter


class Example(SpecificationExtendable):
    """
    In all cases, the example value is expected to be compatible with the type
    schema of its associated value.

    See: `https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.1.md#example-object`_

    :param summary: Short description for the example.
    :param description: Long description for the example.
    :param value: Embedded literal example. The value field and externalValue
        field are mutually exclusive.
    :param external_value: A URL that points to the literal example. This
        provides the capability to reference examples that cannot easily be
        included in JSON or YAML documents. The value field and externalValue
        field are mutually exclusive.

    """
    def __init__(self, value: OpenApiAny=None, summary: str=None, description: str=None, external_value: str=None):
        if value and external_value:
            raise ValueError("value and external_value are mutually exclusive")

        super().__init__()
        self.value = value
        self.summary = summary
        self.description = description
        self.external_value = external_value

    def to_openapi(self) -> OpenApiObject:
        """
        Output OpenAPI specification values.
        """
        return dict_filter({
            'summary': self.summary,
            'description': self.description,
            'value': self.value,
            'externalValue': self.external_value,
        }, base=super().to_openapi())
