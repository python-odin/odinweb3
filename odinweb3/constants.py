import enum


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


class Type(enum.Enum):
    """
    Types defined by OpenAPI Spec
    """
    Integer = 'integer', int
    Number = 'number', float
    String = 'string', str
    Boolean = 'boolean', bool
    Array = 'array', list
    Object = 'object', dict


# class Format:
#     Integer = 'int32', Type.Integer
#     Long = 'int64', Type.Integer
#     Float = 'float', Type.Number
#     Double = 'double', Type.Number
#     Byte = 'byte', Type.String
#     Binary = 'binary', Type.String
#     Date = 'date', Type.String
#     DateTime = 'date-time', Type.String
#     Password = 'password', Type.String