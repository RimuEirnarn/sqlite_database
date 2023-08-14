"""SQLite Functions, this provide 'low level interface'."""

from typing import NamedTuple, Any

from ._utils import check_one

class ParsedFn(NamedTuple):
    """Next step to query_builder"""
    name: str
    values: tuple[Any, ...]

class Function: # pylint: disable=too-few-public-methods
    """Provide Function API calls"""
    def __init__(self, name: str):
        self._name = check_one(name)

    def __call__(self, *args):
        return ParsedFn(self._name, args)

    @property
    def name(self):
        """Name of the function"""
        return self._name
