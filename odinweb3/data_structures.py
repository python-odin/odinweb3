from typing import NamedTuple, Union, Optional

from .constants import Type


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
