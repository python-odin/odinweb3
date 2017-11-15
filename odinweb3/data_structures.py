from typing import NamedTuple, Union, Optional, Dict, Any, Iterable, Tuple, Hashable, List

from .constants import Type, Status
from .exceptions import MultiValueDictKeyError
from .typing import StringMap


class DefaultResource(object):
    """
    A helper object that indicates that the default resource should be used.

    The default resource is then obtained from the bound object.

    """
    def __new__(cls):
        return DefaultResource


class HttpResponse(object):
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


PathParam = NamedTuple('PathParam', [('name', str), ('type', Type), ('type_args', Optional[str])])
PathParam.__new__.__defaults__ = (None, Type.Integer, None)


class UrlPath:
    """
    Object that represents a URL path.
    """
    __slots__ = ('_nodes',)

    @classmethod
    def from_object(cls, obj: Union['UrlPath', str, PathParam]) -> 'UrlPath':
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
                    type_ = Type.Integer

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
        if isinstance(other, _compat.string_types):
            return self + UrlPath.parse(other)
        if isinstance(other, PathParam):
            return UrlPath(*_add_nodes(self._nodes, (other,)))
        return NotImplemented

    def __radd__(self, other):
        # type: (Union[str, PathParam]) -> UrlPath
        if isinstance(other, _compat.string_types):
            return UrlPath.parse(other) + self
        if isinstance(other, PathParam):
            return UrlPath(*_add_nodes((other,), self._nodes))
        return NotImplemented

    def __eq__(self, other):
        # type: (UrlPath) -> bool
        if isinstance(other, UrlPath):
            return self._nodes == other._nodes  # pylint:disable=protected-access
        return NotImplemented

    def __getitem__(self, item):
        # type: (Union[int, slice]) -> UrlPath
        return UrlPath(*force_tuple(self._nodes[item]))

    def apply_args(self, **kwargs):
        # type: (**str) -> UrlPath
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
    def is_absolute(self):
        # type: () -> bool
        """
        Is an absolute URL
        """
        return len(self._nodes) and self._nodes[0] == ''

    @property
    def path_nodes(self):
        """
        Return iterator of PathNode items
        """
        return (n for n in self._nodes if isinstance(n, PathParam))

    @staticmethod
    def odinweb_node_formatter(path_node):
        # type: (PathParam) -> str
        """
        Format a node to be consumable by the `UrlPath.parse`.
        """
        args = [path_node.name]
        if path_node.type:
            args.append(path_node.type.name)
        if path_node.type_args:
            args.append(path_node.type_args)
        return "{{{}}}".format(':'.join(args))

    def format(self, node_formatter=None):
        # type: (Optional[Callable[[PathParam], str]]) -> str
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

NoPath = UrlPath()


class NotDefined(object):
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

    def add(self, key, value):
        # type: (Hashable, Any) -> None
        """
        Adds a new value for the key.

        :param key: the key for the value.
        :param value: the value to add.

        """
        dict.setdefault(self, key, []).append(value)

    def get(self, key, default=None, type_=None):
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

    def getlist(self, key, type_=None):
        # type: (Hashable, Callable) -> List[Any]
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

    def setlist(self, key, new_list):
        # type: (Hashable, List[Any]) -> None
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

    def setdefault(self, key, default=None):
        # type: (Hashable, Any) -> Any
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

    def setlistdefault(self, key, default_list=None):
        # type: (Hashable, List[Any]) -> List[Any]
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

    def items(self, multi=False):
        # type: (bool) -> Iterator[Tuple[Hashable, Any]]
        """
        Return an iterator of ``(key, value)`` pairs.

        :param multi: If set to `True` the iterator returned will have a pair
                      for each value of each key.  Otherwise it will only
                      contain pairs for the lasted added of each key.
        """
        for key, values in iteritems(self):
            if multi:
                for value in values:
                    yield key, value
            else:
                yield key, values[-1]

    iteritems = items

    def sorteditems(self, multi=False):
        # type: (bool) -> Iterator[Tuple[Hashable, Any]]
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

    def lists(self):
        # type: () -> Iterator[Tuple[Hashable, List[Any]]]
        """
        Return a list of ``(key, values)`` pairs, where values is the list
        of all values associated with the key.
        """
        for key, values in iteritems(self):
            yield key, list(values)

    def values(self, multi=False):
        # type: (bool) -> Iterator[Any]
        """
        Yield the last value on every key list.

        :param multi: If set to `True` the iterator returned will have a pair
                      for each value of each key.  Otherwise it will only
                      contain pairs for the lasted added of each key.

        """
        for values in itervalues(self):
            if multi:
                for value in values:
                    yield value
            else:
                yield values[-1]

    itervalues = values

    def valuelists(self):
        # type: (bool) -> Iterator[List[Any]]
        """
        Return an iterator of all values associated with a key.  Zipping
        :meth:`keys` and this is the same as calling :meth:`lists`:

        >>> d = MultiValueDict({"foo": [1, 2, 3]})
        >>> zip(d.keys(), d.valuelists()) == d.lists()
        True

        """
        return itervalues(self)

    def copy(self):
        """Return a shallow copy of this object."""
        return self.__class__(self)

    def to_dict(self, flat=True):
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

    def pop(self, key, default=NotDefined):
        # type: (Hashable, Any) -> Any
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

    def poplist(self, key):
        # type: (Hashable) -> List[Any]
        """
        Pop the list for a key from the dict.  If the key is not in the dict
        an empty list is returned.
        """
        return dict.pop(self, key, [])
