from typing import Any, Dict, Callable, Optional, Union, List

OpenApiAny = Optional[Union[str, int, float, bool, List['EncodedType'], Dict[str, 'EncodedType']]]
"""
Any types supported by Open API (used as to_openapi response type) 
"""

OpenApiObject = Dict[str, OpenApiAny]
"""
The OpenAPI Object type.
"""

# Mapping of strings (commonly used for headers)
StringMap = Dict[str, str]

# Method that resolves an object to a string
StringResolver = Callable[[Any], Optional[str]]
