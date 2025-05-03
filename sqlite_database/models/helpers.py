"""Model helpers"""
# pylint: disable=invalid-name,too-few-public-methods,abstract-method

from typing import Any, Callable, Type, TypeAlias, TypeVar
from enum import StrEnum

import sqlite_database
from .errors import ValidationError
from ..column import BuilderColumn, text, integer, blob, boolean

TypeFunction: TypeAlias = Callable[[str], BuilderColumn]
Model = TypeVar("Model", bound="sqlite_database.BaseModel")

TYPES: dict[Type[Any], TypeFunction] = { # pylint: disable=possibly-used-before-assignment
    int: integer,
    str: text,
    bytes: blob,
    bool: boolean
}

class ConstraintEnum(StrEnum):
    """Constraints for update/delete"""
    RESTRICT = "restrict"
    SETNULL = "null"
    CASCADE = "cascade"
    NOACT = "no act"
    DEFAULT = "default"

RESTRICT = ConstraintEnum.RESTRICT
SETNULL = ConstraintEnum.SETNULL
CASCADE = ConstraintEnum.CASCADE
NOACT = ConstraintEnum.NOACT
DEFAULT = ConstraintEnum.DEFAULT

class Constraint:
    """Base constraint class for models"""
    def __init__(self, column: str) -> None:
        self._column = column

    @property
    def column(self):
        """Columns"""
        return self._column

    def apply(self, type_: BuilderColumn):
        """Apply this constraint to an column"""
        raise NotImplementedError()

class Unique(Constraint):
    """Unique constraint"""

    def apply(self, type_: BuilderColumn):
        type_.unique()

class Foreign(Constraint):
    """Foreign constraint"""

    def __init__(self, column: str, target: str | Type[Model]) -> None:
        super().__init__(column)
        self._target = target
        self.resolve()
        self._base = target
        self._on_delete = DEFAULT
        self._on_update = DEFAULT

    @property
    def target(self):
        """Target foreign constraint"""
        return self._target

    def on_delete(self, constraint: ConstraintEnum):
        """On delete constraint"""
        self._on_delete = constraint
        return self

    def on_update(self, constraint: ConstraintEnum):
        """On update constraint"""
        self._on_update = constraint
        return self

    def resolve(self):
        """Resolve if current target is a Model"""
        if issubclass(self._target, sqlite_database.BaseModel): # type: ignore
            name = self._target.__table_name__
            target = self._target._primary # pylint: disable=protected-access
            if not target:
                raise ValueError(f"{type(self._target)} does not have primary key")
            self._target = f"{name}/{target}"

    def apply(self, type_: BuilderColumn):
        type_.foreign(self._target) # type: ignore
        if self._on_delete != DEFAULT:
            type_.on_delete(self._on_delete.value)
        if self._on_update != DEFAULT:
            type_.on_update(self._on_update.value)

class Primary(Constraint):
    """Primary constraint"""

    def apply(self, type_: BuilderColumn):
        """Apply this constraint as primary"""
        type_.primary()

class Validators():
    """Base class to hold validators"""

    def __init__(self, fn: Callable[[Any], bool], if_fail: str) -> None:
        self._callable = fn
        self._reason = if_fail

    def validate(self, value: Any):
        """Validate a value"""
        if not self._callable(value):
            err = ValidationError(self._reason)
            err.add_note(str(value))
            raise err
        return True
