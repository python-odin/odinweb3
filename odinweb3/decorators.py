"""
Decorators
"""
from odin import getmeta
from odin.utils.collections import force_tuple
from typing import Callable, Any, Union, Iterable, Dict, Generator, Tuple, Set, Sequence

from odinweb3.helpers import create_response
from .bases import HttpRequestBase
from .constants import Method
from .data_structures import NoPath, UrlPath, Path, MiddlewareList, DefaultResponse, PathTypes, Parameter
from .resources import Error
from .utils import dict_filter

Callback = Callable[[HttpRequestBase, ...], Any]


class Operation:
    """
    Container that defines an API operation. An OpenAPI operation is defined
    as a path and a HTTP method.
    """
    _operation_count = 0

    priority = 100  # Set limit high as this should be the last item

    __slots__ = (
        'base_callback', 'callback', 'url_path', 'methods', 'sort_key',
        'middleware', 'summary', 'external_docs', 'parameters',
        'request_body', 'responses', 'deprecated', 'security', 'servers',
        'path', 'operation_id', '_resource', '_binding', '_tags', 'parent',
    )

    def __init__(self, callback: Callback, path: PathTypes=NoPath, methods: Union[Method, Iterable[Method]]=Method.Get,
                 resource=None, tags: Sequence[str]=None, summary: str=None, middleware: Sequence[Any]=None) -> None:
        # Store callback (base is to allow decorators to be applied to callback and still have access to the "base")
        self.base_callback = self.callback = callback
        self.operation_id = "{}.{}".format(callback.__module__, callback.__name__)

        # Path + methods define a "unique" operation
        self.url_path = url_path = UrlPath.from_object(path)
        self.path = url_path.apply_args(id=self.key_field_name)
        self.methods = tuple(methods) if isinstance(methods, Iterable) else (methods,)

        self._resource = resource
        self._tags = set(force_tuple(tags))
        self.summary = summary

        # Configure any middleware assigned to this operation
        self.middleware = MiddlewareList(middleware or [])
        self.middleware.append(self)  # Add self as middleware to obtain pre-dispatch support

        # Sorting
        self.sort_key = Operation._operation_count
        Operation._operation_count += 1

        self._binding = None  # If this operation is bound to a Resource API
        self.parent = None   # If the operation is bound to a container

        # Documentation
        self.external_docs = None
        self.parameters = set()
        self.request_body = None
        self.responses = set()
        self.deprecated = False
        self.security = None
        self.servers = None

        # Copy values from callback (if defined)
        for attr in ('external_docs', 'parameters', 'request_body',
                     'responses', 'deprecated', 'security', 'servers'):
            value = getattr(callback, attr, None)
            if value is not None:
                setattr(self, attr, value)

        # Add a default response
        self.responses.add(DefaultResponse('Unhandled error', Error))

    def __call__(self, request: HttpRequestBase, path_args: Dict[Any]):
        """
        Main wrapper around the operation callback function.
        """
        # path_args is passed by ref so changes can be made.
        for middleware in self.middleware.pre_dispatch:
            middleware(request, path_args)

        response = self.execute(request, **path_args)

        for middleware in self.middleware.post_dispatch:
            response = middleware(request, response)

        return response

    def __eq__(self, other):
        """
        Compare two Operations to identify if they refer to the same endpoint.

        Basically this means does the URL path and methods match?
        """
        if isinstance(other, Operation):
            return all(getattr(self, a) == getattr(other, a) for a in ('path', 'methods'))
        return NotImplemented

    def __hash__(self):
        pass

    def __str__(self):
        return "{} - {} {}".format(self.operation_id, '|'.join(m.value for m in self.methods), self.path)

    def __repr__(self):
        return "Operation({!r}, {!r}, {})".format(self.operation_id, self.path, self.methods)

    def execute(self, request: HttpRequestBase, *args, **path_args) -> Any:
        """
        Execute the callback (binding callback if required)
        """
        binding = self._binding
        if binding:
            # Provide binding as decorators are executed prior to binding
            return self.callback(binding, request, *args, **path_args)
        else:
            return self.callback(request, *args, **path_args)

    def bind_to_instance(self, instance) -> None:
        """
        Bind a ResourceApi instance to an operation.
        """
        self.parent = self._binding = instance
        self.middleware.append(instance)

    def bind_to_container(self, parent) -> None:
        """
        Bind to a ApiContainer
        """
        self.parent = parent

    def operation_items(self, path_prefix: Path=None) -> Generator[Tuple[UrlPath, 'Operation']]:
        """
        Yield operations paths stored in containers.
        """
        url_path = self.path
        if path_prefix:
            url_path = path_prefix + url_path

        yield url_path, self

    @property
    def resource(self):
        """
        Resource associated with operation.
        """
        if self._resource:
            return self._resource
        elif self._binding:
            return self._binding.resource

    @property
    def key_field_name(self) -> str:
        """
        Field identified as the key.
        """
        name = 'resource_id'
        if self.resource:
            key_field = getmeta(self.resource).key_field
            if key_field:
                name = key_field.attname
        return name

    @property
    def is_bound(self) -> bool:
        """
        Operation is bound to a resource api
        """
        return bool(self._binding)

    # Docs ####################################################################

    def to_openapi(self):
        """
        Generate a dictionary for documentation generation.
        """
        return dict_filter(

        )

    @property
    def tags(self) -> Set[str]:
        """
        Tags applied to operation.
        """
        tags = set()
        if self._tags:
            tags.update(self._tags)
        if self._binding:
            binding_tags = getattr(self._binding, 'tags', None)
            if binding_tags:
                tags.update(binding_tags)
        return tags


def operation(path: PathTypes=NoPath, methods: Union[Method, Iterable[Method]]=Method.Get,
              resource=None, tags: Sequence[str]=None, summary: str=None, middleware: Sequence[Any]=None) -> Operation:
    """
    Decorator for defining an API operation. Usually one of the helpers
    (listing, detail, update, delete) would be used in place of this Operation
    decorator.
    """
    def inner(callback):
        return Operation(callback, path, methods, resource, tags, summary, middleware)
    return inner


class ListOperation(Operation):
    """
    Decorator to indicate a listing endpoint.

    Usage::

        class ItemApi(ResourceApi):
            resource = Item

            @listing(path=PathType.Collection, methods=Method.Get)
            def list_items(self, request, offset, limit):
                ...
                return items

    """
    default_offset = 0
    """
    Default offset if not specified.
    """

    default_limit = 50
    """
    Default limit of not specified.
    """

    max_limit = None
    """
    Maximum limit.
    """

    def __init__(self, *args, **kwargs):
        self.listing_resource = kwargs.pop('listing_resource', self.listing_resource)
        self.default_offset = kwargs.pop('default_offset', self.default_offset)
        self.default_limit = kwargs.pop('default_limit', self.default_limit)
        self.max_limit = kwargs.pop('max_limit', self.max_limit)

        super().__init__(*args, **kwargs)

        # Apply documentation
        self.parameters.add(Parameter.query('offset', "Offset to start listing from."))
                                        # default=self.default_offset))
        self.parameters.add(Parameter.query('limit', "Limit on the number of listings returned."))
                                        # default=self.default_limit, maximum=self.max_limit))

    def execute(self, request, *args, **path_args):
        # Get paging args from query string
        offset = int(request.GET.get('offset', self.default_offset))
        if offset < 0:
            offset = 0
        path_args['offset'] = offset

        max_limit = self.max_limit
        limit = int(request.GET.get('limit', self.default_limit))
        if limit < 1:
            limit = 1
        elif max_limit and limit > max_limit:
            limit = max_limit
        path_args['limit'] = limit

        # Run base execute
        result = super().execute(request, *args, **path_args)
        if result is not None:
            if isinstance(result, tuple) and len(result) == 2:
                result, total_count = result
            else:
                total_count = None

            # Return a response (use headers for paging info)
            return create_response(request, result, headers={
                'X-Page-Limit': str(limit),
                'X-Page-Offset': str(offset),
                'X-Total-Count': str(total_count)
            })
