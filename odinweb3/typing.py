from typing import Any, Dict, Callable, Optional

# Mapping of strings (commonly used for headers)
StringMap = Dict[str, str]

# Method that resolves an object to a string
StringResolver = Callable[[Any], Optional[str]]
