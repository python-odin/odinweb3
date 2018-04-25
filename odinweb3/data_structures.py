import re

from odin import Resource, getmeta
from odin.utils.collections import force_tuple
from odin.utils.decorators import lazy_property
from typing import Type, NamedTuple, Union, Optional, Dict, Any, Iterable, Tuple, Hashable, List, Callable, Iterator

from .bases import HttpRequestBase, SpecificationExtendable
from .constants import Status, Location, DataType
from .exceptions import MultiValueDictKeyError
from .typing import StringMap, OpenApiObject
from .utils import sort_by_priority, dict_filter


class DefaultResource:
    """
    A helper object that indicates that the default resource should be used.

    The default resource is then obtained from the bound object.

    """
    def __new__(cls):
        return DefaultResource


class HttpResponse:
    """
    Simplified HTTP response
    """
    __slots__ = ('status', 'body', 'headers')

    @classmethod
    def from_status(cls, status: Union[Status, str], headers: StringMap=None) -> 'HttpResponse':
        return cls(status.description or status.phrase, status, headers)

    def __init__(self, body: Any, status: Union[Status, str]=Status.OK, headers: StringMap=None):
        self.body = body
        self.status = status.value if isinstance(status, Status) else status
        self.headers = headers or {}

    def __getitem__(self, header: str) -> str:
        return self.headers[header]

    def __setitem__(self, header: str, value: str):
        self.headers[header] = value

    def __repr__(self):
        return "<{} {!r}>".format(self.__class__.__name__, self.status)

    @property
    def content_type(self) -> str:
        """
        Get the Content Type header
        """
        return self.headers.get('Content-Type')

    @content_type.setter
    def content_type(self, value: str):
        """
        Set the Content Type header
        """
        self.headers['Content-Type'] = value


class DefaultHttpResponse(HttpResponse):
    """
    Default response object
    """
    def __init__(self, description: str, resource: Optional[Resource]=DefaultResource):
        super(DefaultHttpResponse, self).__init__('default', description, resource)


PathParam = NamedTuple('PathParam', [
    ('name', str),
    ('type', Type),
    ('type_args', Optional[str])
])
PathParam.__new__.__defaults__ = (None, DataType.Integer, None)


def _add_nodes(a, b):
    if b and b[0] == '':
        raise ValueError("Right hand argument cannot be absolute.")
    return a + b


def _to_openapi(base: StringMap=None, description: str=None,
                resource: Resource=None, options: StringMap=None) -> StringMap:
    """
    Common to Open API definition.

    :param base: The base dict.
    :param description: An optional description.
    :param resource: An optional resource.
    :param options: Any additional options

    """
    definition = dict_filter(base or {}, options or {})

    if description:
        definition['description'] = description.format(
            name=getmeta(resource).name if resource else "UNKNOWN"
        )

    # if resource:
    #     definition['schema'] = {
    #         '$ref': '#/definitions/{}'.format(getmeta(resource).resource_name)
    #     }

    return definition


# Naming scheme that follows standard python naming rules for variables/methods
PATH_NODE_RE = re.compile(r'^{([a-zA-Z]\w*)(?::([a-zA-Z]\w*))?(?::([-^$+*:\w\\\[\]|]+))?}$')


PathTypes = Union['UrlPath', str, PathParam]


class UrlPath:
    """
    Object that represents a URL path.
    """
    __slots__ = ('_nodes',)

    @classmethod
    def from_object(cls, obj: PathTypes) -> 'UrlPath':
        """
        Attempt to convert any object into a UrlPath.

        Raise a value error if this is not possible.
        """
        if isinstance(obj, UrlPath):
            return obj
        if isinstance(obj, str):
            return UrlPath.parse(obj)
        if isinstance(obj, PathParam):
            return UrlPath(obj)
        if isinstance(obj, (tuple, list)):
            return UrlPath(*obj)
        raise ValueError("Unable to convert object to UrlPath `%r`" % obj)

    @classmethod
    def parse(cls, url_path: str) -> 'UrlPath':
        """
        Parse a string into a URL path (simple eg does not support typing of URL parameters)
        """
        if not url_path:
            return cls()

        nodes = []
        for node in url_path.rstrip('/').split('/'):
            # Identifies a PathNode
            if '{' in node or '}' in node:
                m = PATH_NODE_RE.match(node)
                if not m:
                    raise ValueError("Invalid path param: {}".format(node))

                # Parse out name and type
                name, param_type, param_arg = m.groups()
                try:
                    type_ = Type[param_type]
                except KeyError:
                    if param_type is not None:
                        raise ValueError("Unknown param type `{}` in: {}".format(param_type, node))
                    type_ = DataType.Integer

                nodes.append(PathParam(name, type_, param_arg))
            else:
                nodes.append(node)

        return cls(*nodes)

    def __init__(self, *nodes: Union[str, PathParam]):
        self._nodes = nodes

    def __hash__(self):
        return hash(str(self))

    def __str__(self):
        return self.format()

    def __repr__(self):
        return "<{} {}>".format(
            self.__class__.__name__,
            ', '.join(repr(n) for n in self._nodes)
        )

    def __add__(self, other):
        # type: (Union[UrlPath, str, PathParam]) -> UrlPath
        if isinstance(other, UrlPath):
            return UrlPath(*_add_nodes(self._nodes, other._nodes))  # pylint:disable=protected-access
        if isinstance(other, str):
            return self + UrlPath.parse(other)
        if isinstance(other, PathParam):
            return UrlPath(*_add_nodes(self._nodes, (other,)))
        return NotImplemented

    def __radd__(self, other: Union[str, PathParam]) -> 'UrlPath':
        if isinstance(other, str):
            return UrlPath.parse(other) + self
        if isinstance(other, PathParam):
            return UrlPath(*_add_nodes((other,), self._nodes))  # pylint:disable=protected-access
        return NotImplemented

    def __eq__(self, other: 'UrlPath') -> bool:
        if isinstance(other, UrlPath):
            return self._nodes == other._nodes  # pylint:disable=protected-access
        return NotImplemented

    def __getitem__(self, idx: Union[int, slice]) -> 'UrlPath':
        return UrlPath(*force_tuple(self._nodes[idx]))

    def apply_args(self, **kwargs: str) -> 'UrlPath':
        """
        Apply formatting to each path node.

        This is used to apply a name to nodes (used to apply key names) eg:

        >>> a = UrlPath("foo", PathParam('{id}'), "bar")
        >>> b = a.apply_args(id="item_id")
        >>> b.format()
        'foo/{item_id}/bar'

        """

        def apply_format(node):
            if isinstance(node, PathParam):
                return PathParam(node.name.format(**kwargs), node.type, node.type_args)
            else:
                return node

        return UrlPath(*(apply_format(n) for n in self._nodes))

    @property
    def is_absolute(self) -> bool:
        """
        Is an absolute URL
        """
        return len(self._nodes) and self._nodes[0] == ''

    @property
    def path_nodes(self) -> Iterable[PathParam]:
        """
        Return iterator of PathNode items
        """
        return (n for n in self._nodes if isinstance(n, PathParam))

    @staticmethod
    def odinweb_node_formatter(path_node: PathParam) -> str:
        """
        Format a node to be consumable by the `UrlPath.parse`.
        """
        args = [path_node.name]
        if path_node.type:
            args.append(path_node.type.name)
        if path_node.type_args:
            args.append(path_node.type_args)
        return "{{{}}}".format(':'.join(args))

    def format(self, node_formatter: Optional[Callable[(PathParam,), str], str]=None) -> str:
        """
        Format a URL path.

        An optional `node_parser(PathNode)` can be supplied for converting a
        `PathNode` into a string to support the current web framework.

        """
        if self._nodes == ('',):
            return '/'
        else:
            node_formatter = node_formatter or self.odinweb_node_formatter
            return '/'.join(node_formatter(n) if isinstance(n, PathParam) else n for n in self._nodes)


# Type definition of a path
Path = Union[UrlPath, PathParam, str]

NoPath = UrlPath()


class Parameter(SpecificationExtendable):
    """
    Describes a single operation parameter.

    A unique parameter is defined by a combination of a name and location.

    :param name: Name of the parameter
    :param location: Location of parameter (query, header, path, cookie)
    :param description: Description of the parameter
    :param required: Indicates if this parameter is mandatory. This value will
        default to the appropriate value based on the location:

        * ``Path``; True
        * All others; False

        If ``False`` is provided with the location set to ``Path`` a
        :class:`ValueError` exception will be raised.
    :param deprecated: This parameter is marked as deprecated in OpenAPI Spec
    :param allow_empty_value:

    """
    @classmethod
    def path(cls, name: str, description: str=None) -> 'Parameter':
        """
        Create a path parameter
        """
        return cls(name, Location.Path, description, True)

    @classmethod
    def query(cls, name: str, description: str=None, required: bool=None,
              deprecated: bool=None, allow_empty_value: bool=None) -> 'Parameter':
        """
        Create a query parameter
        """
        return cls(name, Location.Query, description, required, deprecated, allow_empty_value)

    @classmethod
    def header(cls, name: str, description: str=None, required: bool=None, deprecated: bool=None) -> 'Parameter':
        """
        Create a header parameter
        """
        return cls(name, Location.Header, description, required, deprecated)

    @classmethod
    def cookie(cls, name: str, description: str=None, required: bool=None, deprecated: bool=None) -> 'Parameter':
        """
        Create a cookie parameter
        """
        return cls(name, Location.Cookie, description, required, deprecated)

    __slots__ = ('name', 'location', 'description', 'required', 'deprecated', 'allow_empty_value')

    def __init__(self, name: str, location: Location, description: str=None, required: bool=None,
                 deprecated: bool=None, allow_empty_value: bool=None) -> None:
        if location is Location.Path and required is False:
            raise ValueError("For Path locations, required MUST be True.")

        super().__init__()

        self.name = name
        self.location = location
        self.description = description
        # Default to True for Path locations else False
        self.required = (location is Location.Path) if required is None else bool(required)
        self.deprecated = deprecated
        self.allow_empty_value = allow_empty_value

    def __eq__(self, other: Any) -> bool:
        """
        Determine if another :class:`Parameters` instance is equivalent. The
        OpenAPI specification defines this as a matching name & location.
        """
        if isinstance(other, Parameter):
            return (self.name, self.location) == (other.name, other.location)
        return NotImplemented

    def __and__(self, other: Any) -> 'Parameter':
        """
        Combine parameters. The primary use-case for this method is to extend
        details of a generated param (eg a Path parameter) with documentation.

        The *RHS* of the assignment gets priority.

        """
        if isinstance(other, Parameter):
            return Parameter(
                self.name, self.location,
                other.description or self.description,
                other.required or self.required,
                other.deprecated or self.deprecated,
                other.allow_empty_value or self.allow_empty_value,
            )
        return NotImplemented

    def to_openapi(self) -> OpenApiObject:
        """
        Output OpenAPI specification values.
        """
        return dict_filter({
            'name': self.name,
            'in': self.location.value,
            'description': self.description,
            'required': self.required,
            'deprecated': self.deprecated,
            'allow_empty_value': self.allow_empty_value
        }, base=super().to_openapi())


class Response:
    """
    Definition of a OpenApi response.
    """
    __slots__ = ('status', 'description', 'resource')

    def __init__(self, status: Union[str, Status], description: str=None,
                 resource: Optional[Resource]=DefaultResource):
        self.status = status
        self.description = description
        self.resource = resource

    def __hash__(self):
        return hash(self.status)

    def __str__(self):
        description = self.description or self.status.description
        if description:
            return "{} {} - {}".format(self.status.value, self.status.phrase, description)
        else:
            return "{} {}".format(self.status.value, self.status.phrase)

    def __repr__(self):
        return "Response({!r}, {!r}, {!r})".format(self.status, self.description, self.resource)

    def __eq__(self, other):
        if isinstance(other, Response):
            return hash(self) == hash(other)
        return NotImplemented

    # def to_spec(self, bound_resource=None):
    #     """
    #     Generate a swagger representation.
    #     """
    #     response_def = _to_swagger(
    #         description=self.description,
    #         resource=bound_resource if self.resource is DefaultResource else self.resource,
    #     )
    #     status = self.status if self.status == 'default' else self.status.value
    #     return status, response_def


class DefaultResponse(Response):
    """
    Default response object
    """
    def __init__(self, description: str, resource: Optional[Type[Resource]]=DefaultResource):
        super(DefaultResponse, self).__init__('default', description, resource)


class MiddlewareList(list):
    """
    List of middleware with filtering and sorting builtin.
    """
    @lazy_property
    def pre_request(self) -> Iterable[Callable[(HttpRequestBase,), None]]:
        """
        List of pre-request methods from registered middleware.
        """
        middleware = sort_by_priority(self)
        return tuple(m.pre_request for m in middleware if hasattr(m, 'pre_request'))

    @lazy_property
    def pre_dispatch(self) -> Iterable[Callable[(HttpRequestBase,), None]]:
        """
        List of pre-dispatch methods from registered middleware.
        """
        middleware = sort_by_priority(self)
        return tuple(m.pre_dispatch for m in middleware if hasattr(m, 'pre_dispatch'))

    @lazy_property
    def post_dispatch(self) -> Iterable[Callable[(HttpRequestBase,), HttpResponse]]:
        """
        List of post-dispatch methods from registered middleware.
        """
        middleware = sort_by_priority(self, reverse=True)
        return tuple(m.post_dispatch for m in middleware if hasattr(m, 'post_dispatch'))

    @lazy_property
    def handle_500(self) -> Iterable[Callable[(HttpRequestBase, Exception), HttpResponse]]:
        """
        List of handle-error methods from registered middleware.
        """
        middleware = sort_by_priority(self, reverse=True)
        return tuple(m.handle_500 for m in middleware if hasattr(m, 'handle_500'))

    @lazy_property
    def post_request(self) -> Iterable[Callable[(HttpRequestBase,), HttpResponse]]:
        """
        List of post_request methods from registered middleware.
        """
        middleware = sort_by_priority(self, reverse=True)
        return tuple(m.post_request for m in middleware if hasattr(m, 'post_request'))

    @lazy_property
    def post_spec(self):
        """
        List of post-spec methods from registered middleware.

        This is used to modify documentation (eg add/remove any extra information, provided by the middleware)

        """
        middleware = sort_by_priority(self)
        return tuple(m.post_swagger for m in middleware if hasattr(m, 'post_swagger'))


class NotDefined:
    pass


class MultiValueDict(dict):
    """
    A subclass of dictionary customized to handle multiple values for the
    same key.
    >>> d = MultiValueDict({'name': ['Adrian', 'Simon'], 'position': ['Developer']})
    >>> d['name']
    'Simon'
    >>> d.getlist('name')
    ['Adrian', 'Simon']
    >>> d.getlist('doesnotexist')
    []
    >>> d.getlist('doesnotexist', ['Adrian', 'Simon'])
    ['Adrian', 'Simon']
    >>> d.get('lastname', 'nonexistent')
    'nonexistent'
    >>> d.setlist('lastname', ['Holovaty', 'Willison'])
    This class exists to solve the irritating problem raised by cgi.parse_qs,
    which returns a list for every key, even though most Web forms submit
    single name-value pairs.

    This data structure is based off Flask and Django implementations. The
    main differences are as follows:

    - Unlike Flask the last added value is used this is the same same
      behaviour as Django/Bottle
    - Includes Flask/Bottle type conversions
    - Includes pop methods not supported by Django

    """
    def __init__(self, mapping: Union['MultiValueDict', dict, Iterable[Tuple[str, str]]]=None):
        if isinstance(mapping, MultiValueDict):
            dict.__init__(self, ((k, l[:]) for k, l in mapping.lists()))

        elif isinstance(mapping, dict):
            tmp = {}
            for key, value in mapping.items():
                if isinstance(value, (tuple, list)):
                    if len(value) == 0:
                        continue
                    value = list(value)
                else:
                    value = [value]
                tmp[key] = value
            dict.__init__(self, tmp)

        elif mapping:
            tmp = {}
            for key, value in mapping:
                tmp.setdefault(key, []).append(value)
            dict.__init__(self, tmp)

        else:
            dict.__init__(self)

    def __getstate__(self) -> Dict[Hashable, List[Any]]:
        return dict(self.lists())

    def __setstate__(self, value):
        dict.clear(self)
        dict.update(self, value)

    def __getitem__(self, key: Hashable) -> Any:
        """
        Return the last data value for this key, or [] if it's an empty list;
        raise KeyError if not found.
        """
        try:
            return dict.__getitem__(self, key)[-1]
        except LookupError:
            raise MultiValueDictKeyError(key)

    def __setitem__(self, key: Hashable, value: Any):
        """
        Like :meth:`add` but removes an existing key first.

        :param key: the key for the value.
        :param value: the value to set.

        """
        dict.__setitem__(self, key, [value])

    def __copy__(self):
        return self.copy()

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, list(self.items(multi=True)))

    def add(self, key: Hashable, value: Any):
        """
        Adds a new value for the key.

        :param key: the key for the value.
        :param value: the value to add.

        """
        dict.setdefault(self, key, []).append(value)

    def get(self, key: Hashable, default: Any=None, type_: type=None):
        """
        Return the last data value for the passed key. If key doesn't exist
        or value is an empty list, return `default`.
        """
        try:
            rv = self[key]
        except KeyError:
            return default
        if type_ is not None:
            try:
                rv = type_(rv)
            except ValueError:
                rv = default
        return rv

    def getlist(self, key: Hashable, type_: type=None) -> List[Any]:
        """
        Return the list of items for a given key. If that key is not in the
        `MultiDict`, the return value will be an empty list.  Just as `get`
        `getlist` accepts a `type` parameter.  All items will be converted
        with the callable defined there.

        :param key: The key to be looked up.
        :param type_: A callable that is used to cast the value in the
                     :class:`MultiDict`.  If a :exc:`ValueError` is raised
                     by this callable the value will be removed from the list.
        :return: a :class:`list` of all the values for the key.

        """
        try:
            rv = dict.__getitem__(self, key)
        except KeyError:
            return []
        if type_ is None:
            return list(rv)
        result = []
        for item in rv:
            try:
                result.append(type_(item))
            except ValueError:
                pass
        return result

    def setlist(self, key: Hashable, new_list: List[Any]):
        """
        Remove the old values for a key and add new ones.  Note that the list
        you pass the values in will be shallow-copied before it is inserted in
        the dictionary.
        >>> d = MultiValueDict()
        >>> d.setlist('foo', ['1', '2'])
        >>> d['foo']
        '1'
        >>> d.getlist('foo')
        ['1', '2']
        :param key: The key for which the values are set.
        :param new_list: An iterable with the new values for the key.  Old values
                         are removed first.
        """
        dict.__setitem__(self, key, list(new_list))

    def setdefault(self, key: Hashable, default: Any=None) -> Any:
        """
        Returns the value for the key if it is in the dict, otherwise it
        returns `default` and sets that value for `key`.

        :param key: The key to be looked up.
        :param default: The default value to be returned if the key is not
                        in the dict.  If not further specified it's `None`.

        """
        if key not in self:
            self[key] = default
        else:
            default = self[key]
        return default

    def setlistdefault(self, key: Hashable, default_list: List[Any]=None) -> List[Any]:
        """
        Like `setdefault` but sets multiple values.  The list returned
        is not a copy, but the list that is actually used internally.  This
        means that you can put new values into the dict by appending items
        to the list:
        >>> d = MultiValueDict({"foo": 1})
        >>> d.setlistdefault("foo").extend([2, 3])
        >>> d.getlist("foo")
        [1, 2, 3]

        :param key: The key to be looked up.
        :param default_list: An iterable of default values.  It is either copied
                             (in case it was a list) or converted into a list
                             before returned.
        :return: a :class:`list`

        """
        if key not in self:
            default_list = list(default_list or ())
            dict.__setitem__(self, key, default_list)
        else:
            default_list = dict.__getitem__(self, key)
        return default_list

    def items(self, multi: bool=False) -> Iterator[Tuple[Hashable, Any]]:
        """
        Return an iterator of ``(key, value)`` pairs.

        :param multi: If set to `True` the iterator returned will have a pair
                      for each value of each key.  Otherwise it will only
                      contain pairs for the lasted added of each key.
        """
        for key, values in dict.items(self):
            if multi:
                for value in values:
                    yield key, value
            else:
                yield key, values[-1]

    def sorteditems(self, multi: bool=False) -> Iterator[Tuple[Hashable, Any]]:
        """
        Return an iterator of ``(key, value)`` pairs, sorted by key.

        :param multi: If set to `True` the iterator returned will have a pair
                      for each value of each key.  Otherwise it will only
                      contain pairs for the lasted added of each key.

        """
        for key in sorted(dict.keys(self)):
            if multi:
                for value in self.getlist(key):
                    yield key, value
            else:
                yield key, self[key]

    def lists(self) -> Iterator[Tuple[Hashable, List[Any]]]:
        """
        Return a list of ``(key, values)`` pairs, where values is the list
        of all values associated with the key.
        """
        for key, values in dict.items(self):
            yield key, list(values)

    def values(self, multi: bool=False) -> Iterator[Any]:
        """
        Yield the last value on every key list.

        :param multi: If set to `True` the iterator returned will have a pair
                      for each value of each key.  Otherwise it will only
                      contain pairs for the lasted added of each key.

        """
        for values in dict.values(self):
            if multi:
                for value in values:
                    yield value
            else:
                yield values[-1]

    def valuelists(self) -> Iterator[List[Any]]:
        """
        Return an iterator of all values associated with a key.  Zipping
        :meth:`keys` and this is the same as calling :meth:`lists`:

        >>> d = MultiValueDict({"foo": [1, 2, 3]})
        >>> zip(d.keys(), d.valuelists()) == d.lists()
        True

        """
        return dict.values(self)

    def copy(self):
        """Return a shallow copy of this object."""
        return self.__class__(self)

    def to_dict(self, flat: True=True):
        """
        Return the contents as regular dict.  If `flat` is `True` the
        returned dict will only have the first item present, if `flat` is
        `False` all values will be returned as lists.

        :param flat: If set to `False` the dict returned will have lists
                     with all the values in it.  Otherwise it will only
                     contain the last value for each key.
        :return: a :class:`dict`

        """
        if flat:
            return dict(self.items())
        return dict(self.lists())

    def pop(self, key: Hashable, default: Any=NotDefined) -> Any:
        """
        Pop the last item for a list on the dict.  Afterwards the
        key is removed from the dict, so additional values are discarded:
        >>> d = MultiValueDict({"foo": [1, 2, 3]})
        >>> d.pop("foo")
        1
        >>> "foo" in d
        False

        :param key: the key to pop.
        :param default: if provided the value to return if the key was
                        not in the dictionary.
        """
        try:
            return dict.pop(self, key)[-1]
        except LookupError:
            if default is NotDefined:
                raise MultiValueDictKeyError(key)
            return default

    def poplist(self, key: Hashable) -> List[Any]:
        """
        Pop the list for a key from the dict.  If the key is not in the dict
        an empty list is returned.
        """
        return dict.pop(self, key, [])
