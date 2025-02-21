"""SQLite Functions, this provide 'low level interface'."""

from typing import NamedTuple, Any
from random import randint

from ._utils import check_one

# It was moved here, so users don't just import anything from query builder.


def _function_extract(parsed: "ParsedFn") -> tuple[str, dict[str, Any]]:
    """Extract function into SQL function syntax."""
    check_one(parsed.name)
    if len(parsed.values) == 1:
        if parsed.values[0] in (None, ..., "*"):
            return f"{parsed.name}(*)", {}
        # need to find a check if input is column name or some values.
        return f"{parsed.name}({check_one(parsed.values[0])})", {}
    string = parsed.name + "("
    data = {}
    # ? we don't know how many same function calls at the same time, though we can use count param.
    suffix = randint(0, 100000)
    for i, _ in enumerate(parsed.values):
        key = f":{parsed.name}{suffix}_{i}"
        if isinstance(i, ParsedFn):
            data[key] = _function_extract(i)
            continue
        data[key] = i
        string += f"{key}, "
    string = string[:-2] + ")"
    return string, data


class ParsedFn(NamedTuple):
    """Next step to query_builder"""

    name: str
    values: tuple[Any, ...]

    def parse_sql(self):
        """Parse the ParsedFn into SQL"""
        return _function_extract(self)


class Function:  # pylint: disable=too-few-public-methods
    """Provide Function API calls"""

    def __init__(self, name: str):
        self._name = check_one(name)

    def __call__(self, *args):
        return ParsedFn(self._name, args)

    @property
    def name(self):
        """Name of the function"""
        return self._name

count = Function("COUNT")
