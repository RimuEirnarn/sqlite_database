"""Universal utility"""

from typing import Any

from ._utils import Row
from .typings import Queries

# ! Please separate the imports of universal (public util) from core util!
# ! Make sure _utils.py does not import any from this package!


def crunch(query: Queries | list[dict[str, Any]]) -> Row[str, list[Any]]:  # type: ignore
    """Crunch queries into Row that all of its value become a list."""
    data: dict[str, list[Any]] = Row()
    for value in query:
        for key, val in value.items():
            if key not in data:
                data[key] = []
            data[key].append(val)
    return data
