"""Model helpers"""
# pylint: disable=invalid-name,too-few-public-methods,abstract-method

from typing import Any, Callable, Type, TypeAlias
from .column import BuilderColumn, text, integer, blob, boolean

TypeFunction: TypeAlias = Callable[[str], BuilderColumn]

TYPES: dict[Type[Any], TypeFunction] = { # pylint: disable=possibly-used-before-assignment
    int: integer,
    str: text,
    bytes: blob,
    bool: boolean
}


class Constraint:
    """Base constraint class for models"""
    def __init__(self, column: str) -> None:
        self._column = column

    def apply(self, type_: BuilderColumn):
        """Apply this constraint to an column"""
        raise NotImplementedError()

class Unique(Constraint):
    """Unique constraint"""

    def apply(self, type_: BuilderColumn):
        type_.unique()

class Foreign(Constraint):
    """Foreign constraint"""

class Primary(Constraint):
    """Primary constraint"""
