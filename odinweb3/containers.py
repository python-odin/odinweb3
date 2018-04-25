"""
API Containers
~~~~~~~~~~~~~~

Containers that provide structure to an API.

"""
import logging

from collections import OrderedDict
from typing import Union, Tuple, Any, Generator, Dict, Optional, Sequence

from odin import Resource, getmeta
from odin.codecs.json import codec as json_codec
from odin.exceptions import ValidationError

from . import content_type_resolvers
from .bases import HttpRequestBase
from .constants import Method, HTTPStatus
from .data_structures import UrlPath, NoPath, HttpResponse, MiddlewareList
from .decorators import Operation
from .exceptions import ImmediateHttpResponse
from .helpers import resolve_content_type, create_response
from .resources import Error

logger = logging.getLogger(__name__)

DEFAULT_CODECS = {json_codec.content_type: json_codec}

# Attempt to load other codecs that have dependencies
try:
    from odin.codecs.msgpack import codec as msgpack_codec
    DEFAULT_CODECS[msgpack_codec.content_type] = msgpack_codec
except ImportError:
    pass

try:
    from odin.codecs.yaml import codec as yaml_codec
    DEFAULT_CODECS[yaml_codec.content_type] = yaml_codec
except ImportError:
    pass


class ResourceApiMeta(type):
    """
    Meta class that resolves endpoints to routes.
    """
    def __new__(mcs, name, bases, attrs):
        super_new = super(ResourceApiMeta, mcs).__new__

        # attrs will never be empty for classes declared in the standard way
        # (ie. with the `class` keyword). This is quite robust.
        if name == 'NewBase' and attrs == {}:
            return super_new(mcs, name, bases, attrs)

        parents = [
            b for b in bases
            if isinstance(b, ResourceApiMeta) and not (b.__name__ == 'NewBase' and b.__mro__ == (b, object))
        ]
        if not parents:
            # If this isn't a subclass of don't do anything special.
            return super_new(mcs, name, bases, attrs)

        # Determine the resource used by this API (handle inherited resources)
        api_resource = attrs.get('resource')
        if api_resource is None:
            for base in bases:
                api_resource = base.resource
                if api_resource:
                    break

        # Get operations
        operations = []
        for obj in attrs.values():
            if isinstance(obj, Operation):
                operations.append(obj)

        # Get routes from parent objects
        for parent in parents:
            parent_ops = getattr(parent, '_operations', None)
            if parent_ops:
                operations.extend(parent_ops)

        attrs['_operations'] = sorted(operations, key=lambda o: o.sort_key)

        new_class = super_new(mcs, name, bases, attrs)

        return new_class


class ResourceApi(metaclass=ResourceApiMeta):
    """
    Base framework specific ResourceAPI implementations.
    """
    api_name = None  # type: str
    """
    Name of the API endpoint
    """

    resource = None
    """
    The resource this API is modelled on.
    """

    path_prefix = UrlPath()
    """
    Prefix to prepend to any generated path.
    """

    tags = None
    """
    Resource API tags
    """

    parent = None
    """
    Parent container this object is bound to.
    """

    def __init__(self):
        if not self.api_name:
            self.api_name = getmeta(self.resource).name.lower()

        # Append APIs name to path prefix
        self.path_prefix += self.api_name

        for operation in self._operations:
            operation.bind_to_instance(self)

    def bind_to_container(self, parent):
        """
        Bind to a parent container.
        """
        self.parent = parent

    def operation_items(self, path_base):
        # type: (Union[str, UrlPath]) -> Generator[Tuple[UrlPath, Operation]]
        """
        Return all operations stored in containers.
        """
        path_base += self.path_prefix

        for operation in self._operations:
            for op_path in operation.op_paths(path_base):
                yield op_path


ApiChild = Union[Operation, 'ApiContainer', ResourceApi]


class ApiContainer:
    """
    Container or API endpoints.

    This class is intended as a base class for other API classes. Containers
    can also be nested. This is used to support versions etc.

    """
    __slots__ = ('children', 'name', 'path_prefix', 'parent')

    def __init__(self, *children: ApiChild, name: str=None, path_prefix: Union[str, UrlPath]=None) -> None:
        # Set self as the parent
        for child in children:
            child.bind_to_container(self)
        self.children = list(children)

        self.name = name
        if path_prefix:
            self.path_prefix = UrlPath.from_object(path_prefix)
        elif name:
            self.path_prefix = UrlPath.parse(name)
        else:
            self.path_prefix = NoPath

        self.parent = None

    def bind_to_container(self, parent):
        """
        Bind to a parent container.
        """
        self.parent = parent

    def operation(self, path: UrlPath=NoPath, methods: Union[Method, Sequence[Method]]=Method.Get,
                  resource: Resource=None, tags: Sequence[str]=None, summary: str=None,
                  middleware: Sequence[Any]=None) -> Operation:
        """
        Decorator for creating an operation from a simple method. eg::

            >>> api = ApiContainer()
            >>> @api.operation('/my-operation', methods=Method.Post)
            ... def my_operation(request):
            ...     pass

        The `doc` decorators can be used in conjunction with this decorator.

        """
        def inner(callback):
            operation = Operation(callback, path, methods, resource, tags, summary, middleware)
            self.children.append(operation)
            return operation
        return inner

    def operation_items(self, path_base: Union[str, UrlPath]=None) -> Generator[Tuple[UrlPath, Operation]]:
        """
        Yields operation item tuples made up of the path and Operation entries.
        """
        if path_base:
            path_base += self.path_prefix
        else:
            path_base = self.path_prefix or UrlPath()

        for child in self.children:
            yield from child.operation_items(path_base)


ApiCollection = ApiContainer


class ApiVersion(ApiContainer):
    """
    Versioned collection of API children, usually used as the first container
    to hold a specific version of an API.
    """
    def __init__(self, *containers: ApiChild, version: int=1, **options) -> None:
        self.version = version
        options.setdefault('name', 'v{}'.format(self.version))
        super(ApiVersion, self).__init__(*containers, **options)


class ApiInterfaceBase(ApiContainer):
    """
    Base class for API interfaces.

    API interfaces are the interfaces between OdinWeb and the HTTP/WSGI
    framework being utilised.

    """
    registered_codecs = DEFAULT_CODECS
    """
    Codecs that are supported by this API.
    """

    request_type_resolvers = [
        content_type_resolvers.content_type_header(),
        content_type_resolvers.accepts_header(),
        content_type_resolvers.specific_default(json_codec.CONTENT_TYPE),
    ]
    """
    Collection of resolvers used to identify the content type of the request.
    """

    response_type_resolvers = [
        content_type_resolvers.accepts_header(),
        content_type_resolvers.content_type_header(),
        content_type_resolvers.specific_default(json_codec.CONTENT_TYPE),
    ]
    """
    Collection of resolvers used to identify the content type of the response.
    """

    remap_codecs = {
        'text/plain': 'application/json'
    }
    """
    Remap certain codecs commonly mistakenly used.
    """

    def __init__(self, *containers, name: str='api', path_prefix: Union[str, UrlPath]=None,
                 debug_enabled: bool=False, middleware: list=None, options: bool=True):
        self.debug_enabled = debug_enabled
        self.middleware = MiddlewareList(middleware or [])
        self.options = options
        super().__init__(*containers, name=name, path_prefix=path_prefix or name)

        if not self.path_prefix.is_absolute:
            raise ValueError("Path prefix must be an absolute path (eg start with a '/')")

    def handle_500(self, request: HttpRequestBase, exception: Exception) -> Any:
        """
        Handle an *un-handled* exception.
        """
        # Let middleware attempt to handle exception
        try:
            for middleware in self.middleware.handle_500:
                resource = middleware(request, exception)
                # Middleware can be inserted to return a resource to represent
                # an error response.
                if resource:
                    return resource

        except Exception as ex:  # noqa - This is a top level handler
            exception = ex

        # Fallback to generic error
        logger.exception('Internal Server Error: %s', exception, extra={
            'status_code': 500,
            'request': request
        })
        return Error.from_status(HTTPStatus.INTERNAL_SERVER_ERROR, 0,
                                 "An unhandled error has been caught.")

    def dispatch_operation(self, operation: Operation, request: HttpRequestBase,
                           path_args: Dict[str, Any]) -> Tuple[Any, Optional[HTTPStatus], Optional[Dict[str, str]]]:
        """
        Dispatch and handle exceptions from operation.
        """
        try:
            # path_args is passed by ref so changes can be made.
            for middleware in self.middleware.pre_dispatch:
                middleware(request, path_args)

            resource = operation(request, path_args)

            for middleware in self.middleware.post_dispatch:
                resource = middleware(request, resource)

        except ImmediateHttpResponse as e:
            # An exception used to return a response immediately, skipping any
            # further processing.
            return e.resource, e.status, e.headers

        except ValidationError as e:
            # A validation error was raised by a resource.
            if hasattr(e, 'message_dict'):
                resource = Error.from_status(HTTPStatus.BAD_REQUEST, 0, "Failed validation", meta=e.message_dict)
            else:
                resource = Error.from_status(HTTPStatus.BAD_REQUEST, 0, str(e))
            return resource, resource.status, None

        except NotImplementedError:
            resource = Error.from_status(HTTPStatus.NOT_IMPLEMENTED, 0, "The method has not been implemented")
            return resource, resource.status, None

        except Exception as e:
            if self.debug_enabled:
                # If debug is enabled then fallback to the frameworks default
                # error processing, this often provides convenience features
                # to aid in the debugging process.
                raise

            resource = None
            # Fallback to the default handler
            if resource is None:
                resource = self.handle_500(request, e)

            return resource, resource.status, None

        else:
            return resource, None, None

    def _dispatch(self, operation: Operation, request: HttpRequestBase, path_args: Dict[str, Any]):
        """
        Wrapped dispatch method, prepare request and generate a HTTP Response.
        """
        # Determine the request and response types. Ensure API supports the requested types
        request_type = resolve_content_type(self.request_type_resolvers, request)
        request_type = self.remap_codecs.get(request_type, request_type)
        try:
            request.request_codec = self.registered_codecs[request_type]
        except KeyError:
            return HttpResponse.from_status(HTTPStatus.UNPROCESSABLE_ENTITY)

        response_type = resolve_content_type(self.response_type_resolvers, request)
        response_type = self.remap_codecs.get(response_type, response_type)
        try:
            request.response_codec = self.registered_codecs[response_type]
        except KeyError:
            return HttpResponse.from_status(HTTPStatus.NOT_ACCEPTABLE)

        # Check if method is in our allowed method list
        if request.method not in operation.methods:
            return HttpResponse.from_status(
                HTTPStatus.METHOD_NOT_ALLOWED,
                {'Allow': ','.join(m.value for m in operation.methods)}
            )

        # Response types
        resource, status, headers = self.dispatch_operation(operation, request, path_args)

        # Convert status into an integer
        if isinstance(status, HTTPStatus):
            status = status.value

        # Return a HttpResponse and just send it!
        if isinstance(resource, HttpResponse):
            return resource

        # Encode the response
        return create_response(request, resource, status, headers)

    def dispatch(self, operation: Operation, request: HttpRequestBase, **path_args):
        """
        Dispatch incoming request and capture top level exceptions.
        """
        # Add current operation to the request (for convenience in middleware methods)
        request.current_operation = operation

        try:
            for middleware in self.middleware.pre_request:
                middleware(request, path_args)

            response = self._dispatch(operation, request, path_args)

            for middleware in self.middleware.post_request:
                response = middleware(request, response)

        except Exception as ex:
            if self.debug_enabled:
                # If debug is enabled then fallback to the frameworks default
                # error processing, this often provides convenience features
                # to aid in the debugging process.
                raise
            return self.handle_500(request, ex)

        else:
            return response

    def method_collated_operations(self, path_base: Union[str, UrlPath]=None
                                   ) -> OrderedDict[UrlPath, Dict[str, Operation]]:
        """
        Collates path and operations by method. This is required for certain
        web frameworks (eg Django) where it is up the developer to handle
        routing of request method.

        The result is a structure Path -> Method -> Operation.
        """
        paths = OrderedDict()
        for path, operation in self.operation_items(path_base):
            methods = paths.setdefault(path, {})
            for method in operation.methods:
                methods[method] = operation
        return paths
