"""

"""
from typing import Callable, List, Any, Union, Iterable, Dict, Generator, Tuple, Set, Type

from odin.utils import force_tuple, lazy_property, getmeta
from odinweb3.resources import Error, Listing
from odinweb3.utils import dict_filter

from .bases import HttpRequestBase
from .constants import Method, Param
from .data_structures import NoPath, UrlPath, Path, MiddlewareList, DefaultResponse


class Operation:
    """
    Container that defines an API operation. An OpenAPI operation is defined
    as a path and a HTTP method.
    """
    _operation_count = 0

    priority = 100  # Set limit high as this should be the last item

    def __init__(self, callback: Callable[(HttpRequestBase,), Any],
                 path: UrlPath=NoPath, methods: Union[Iterable[Method], Method]=Method.Get,
                 resource=None, tags=None, summary: str=None, middleware: List[Any]=None):
        """
        :param callback: Callback method
        :param path: A sub path to this operation from a parent container.
        :param methods: HTTP method(s) this function response on.
        :param resource:
        :param tags:
        :param summary:
        :param middleware:
        """
        self.base_callback = self.callback = callback
        self.url_path = UrlPath.from_object(path)
        self.methods = tuple(methods) if isinstance(methods, Iterable) else (methods,)
        self._resource = resource

        # Sorting/hashing
        self.sort_key = Operation._operation_count
        Operation._operation_count += 1

        # If this operation is bound to a ResourceAPI
        self._binding = None

        self.middleware = MiddlewareList(middleware or [])
        self.middleware.append(self)  # Add self as middleware to obtain pre-dispatch support

        # Documentation
        self.deprecated = False
        self.summary = summary
        self.consumes = set()
        self.produces = set()
        self.responses = set()
        self.parameters = set()
        self._tags = set(force_tuple(tags))

        # Copy values from callback (if defined)
        for attr in ('deprecated', 'consumes', 'produces', 'responses', 'parameters'):
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
        Compare to Operations to identify if they refer to the same endpoint.

        Basically this means does the URL path and methods match?
        """
        if isinstance(other, Operation):
            return all(
                getattr(self, a) == getattr(other, a)
                for a in ('path', 'methods')
            )
        return NotImplemented

    def __str__(self):
        return "{} - {} {}".format(self.operation_id, '|'.join(m.value for m in self.methods), self.path)

    def __repr__(self):
        return "Operation({!r}, {!r}, {})".format(self.operation_id, self.path, self.methods)

    def execute(self, request, *args, **path_args):
        # type: (Any, tuple, Dict[Any]) -> Any
        """
        Execute the callback (binding callback if required)
        """
        binding = self._binding
        if binding:
            # Provide binding as decorators are executed prior to binding
            return self.callback(binding, request, *args, **path_args)
        else:
            return self.callback(request, *args, **path_args)

    def bind_to_instance(self, instance):
        """
        Bind a ResourceApi instance to an operation.
        """
        self._binding = instance
        self.middleware.append(instance)

    def op_paths(self, path_prefix: Path=None) -> Generator[Tuple[UrlPath, 'Operation']]:
        """
        Yield operations paths stored in containers.
        """
        url_path = self.path
        if path_prefix:
            url_path = path_prefix + url_path

        yield url_path, self

    @lazy_property
    def path(self):
        """
        Prepared and setup URL Path.
        """
        return self.url_path.apply_args(id=self.key_field_name)

    @property
    def resource(self):
        """
        Resource associated with operation.
        """
        if self._resource:
            return self._resource
        elif self._binding:
            return self._binding.resource

    @lazy_property
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

    def to_spec(self):
        """
        Generate a dictionary for documentation generation.
        """
        return dict_filter(
            operationId=self.operation_id,
            description=(self.callback.__doc__ or '').strip() or None,
            summary=self.summary or None,
            tags=list(self.tags) or None,
            deprecated=self.deprecated or None,
            consumes=list(self.consumes) or None,
            parameters=[param.to_swagger(self.resource) for param in self.parameters] or None,
            produces=list(self.produces) or None,
            responses=dict(resp.to_swagger(self.resource) for resp in self.responses) or None,
        )

    @lazy_property
    def operation_id(self):
        return "{}.{}".format(self.base_callback.__module__, self.base_callback.__name__)

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
    listing_resource = Listing
    """
    Resource used to wrap listings.
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

        super(ListOperation, self).__init__(*args, **kwargs)

        # Apply documentation
        self.parameters.add(Param.query('offset', Type.Integer, "Offset to start listing from.",
                                        default=self.default_offset))
        self.parameters.add(Param.query('limit', Type.Integer, "Limit on the number of listings returned.",
                                        default=self.default_limit, maximum=self.max_limit))
        self.parameters.add(Param.query('bare', Type.Boolean, "Return a plain list of objects."))

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

        bare = to_bool(request.GET.get('bare', False))

        # Run base execute
        result = super(ListOperation, self).execute(request, *args, **path_args)
        if result is not None:
            if isinstance(result, tuple) and len(result) == 2:
                result, total_count = result
            else:
                total_count = None

            return result if bare else Listing(result, limit, offset, total_count)
