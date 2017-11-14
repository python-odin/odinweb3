from typing import Dict, Any, List

ApiObject = Dict[str, Any]


class SpecificExtendable:
    """
    Provides specific extensions.

    See `https://swagger.io/specification/#specificationExtensions`_

    """
    __slots__ = ('_x',)

    def __init__(self):
        self._x = {}

    def __getattr__(self, field):
        try:
            return self._x[field]
        except KeyError:
            raise AttributeError('Unknown attribute `{}`'.format(field))

    def __setattr__(self, field, value) -> None:
        self._x[field] = value

    def __delattr__(self, field):
        try:
            del self._x[field]
        except KeyError:
            raise AttributeError('Unknown attribute `{}`'.format(field))

    def to_spec(self):
        """
        Generate spec of data.
        """
        return {'x-' + k: v for k, v in self._x.items()}


class Contact(SpecificExtendable):
    """
    OpenAPI Contact object

    See `https://swagger.io/specification/#contactObject`_

    """
    __slots__ = ('name', 'url', 'email')

    def __init__(self, name: str, url: str=None, email: str=None):
        super().__init__()
        self.name = name
        self.url = url
        self.email = email

    def __repr__(self):
        return "<{} {!r}>".format(self.__class__.__name__, self.name)

    def to_spec(self) -> ApiObject:
        spec = {'name': self.name}
        if self.url:
            spec['url'] = self.url
        if self.email:
            spec['email'] = self.email
        return spec


class License(SpecificExtendable):
    """
    OpenAPI License Object

    See `https://swagger.io/specification/#licenseObject`_

    """
    __slots__ = ('name', 'url')

    def __init__(self, name: str, url: str = None):
        super().__init__()
        self.name = name
        self.url = url

    def __repr__(self):
        return "<{} {!r}>".format(self.__class__.__name__, self.name)

    def to_spec(self) -> ApiObject:
        spec = {'name': self.name}
        if self.url:
            spec['url'] = self.url
        return spec


class ServerVariable(SpecificExtendable):
    """
    OpenAPI Server Variable
    """
    __slots__ = ('default', 'enum', 'description')

    def __init__(self, default: str, description: str=None, enum: List[str]=None):
        super().__init__()
        self.default = default
        self.description = description
        self.enum = enum

    def __repr__(self):
        return "<{} {!r}>".format(self.__class__.__name__, self.default)

    def to_spec(self) -> ApiObject:
        spec = {'default': self.default}
        if self.description:
            spec['description'] = self.description
        if self.enum:
            spec['enum'] = self.enum
        return spec


class Server(SpecificExtendable):
    """
    OpenAPI Server

    See: `https://swagger.io/specification/#serverObject`_

    """
    __slots__ = ('url', 'description', 'variables')

    def __init__(self, url: str, description: str=None, variables: Dict[str, ServerVariable]=None):
        super().__init__()
        self.url = url
        self.description = description
        self.variables = variables

    def __repr__(self):
        return "<{} {!r}>".format(self.__class__.__name__, self.url)

    def to_spec(self) -> ApiObject:
        spec = {'url': self.url}
        if self.description:
            spec['description'] = self.description
        if self.variables:
            spec['variables'] = {k: v.to_spec for k, v in self.variables.items()}
        return spec


class ExternalDocumentation(SpecificExtendable):
    """
    OpenAPI License Object

    See `https://swagger.io/specification/#externalDocumentationObject`_

    """
    __slots__ = ('url', 'description')

    def __init__(self, url: str, description: str = None):
        super().__init__()
        self.url = url
        self.description = description

    def __repr__(self):
        return "<{} {!r}>".format(self.__class__.__name__, self.url)

    def to_spec(self) -> ApiObject:
        spec = {'url': self.url}
        if self.description:
            spec['description'] = self.description
        return spec


class Tag(SpecificExtendable):
    """
    OpenAPI Tag Object

    See `https://swagger.io/specification/#tagObject`_

    """
    __slots__ = ('name', 'description', 'external_docs')

    def __init__(self, name: str, description: str = None, external_docs: ExternalDocumentation=None):
        super().__init__()
        self.name = name
        self.description = description
        self.external_docs = external_docs

    def __repr__(self):
        return "<{} {!r}>".format(self.__class__.__name__, self.name)

    def to_spec(self) -> ApiObject:
        spec = {'name': self.name}
        if self.description:
            spec['description'] = self.description
        if self.external_docs:
            spec['externalDocs'] = self.external_docs.to_spec()
        return spec


class OpenAPI:
    """
    OpenAPI Spec
    """
    SPEC_VERSION = '3.0.0'

    def __init__(self, title: str, version: str, description: str=None):
        self.title = title
        self.version = version
        self.description = description
        self.termsOfService = None
        self.contact = None
        self.license = None

    def to_spec(self) -> dict:
        """
        Generate spec format.
        """
        # Build info
        info = {
            'version': '0.0.0',
            'title': '',
        }
        for attr in ('description', 'termsOfService', 'contact', 'license'):
            value = getattr(self, attr)
            if value:
                info[attr] = value

        # Build top level
        spec = {
            'openapi': self.SPEC_VERSION,
            'info': info,
            'paths': {}
        }

        return spec
