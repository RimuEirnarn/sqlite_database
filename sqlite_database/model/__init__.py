"""Models"""

# pylint: disable=unused-import,unused-argument,cyclic-import

from typing import Any, Protocol, Self, Type, TypeVar, cast
from dataclasses import dataclass, fields, is_dataclass, MISSING

from .helpers import Constraint, Unique, Primary, Foreign, TYPES, Validators
from .query_builder import QueryBuilder
from .errors import ConstraintError
from ..database import Database, Table
from ..column import text, BuilderColumn

NULL = object()
T = TypeVar("T", bound="BaseModel")

## Model functions

class BaseModel:  # pylint: disable=too-few-public-methods
    """Base class for all Models using Model API"""

    __schema__: tuple[Constraint, ...] = ()
    __validators__: tuple[Validators, ...] = ()
    _tbl: Table
    _primary: str | None

    @classmethod
    def create_table(cls, db: Database):
        """Create database according to annotations and schema from `__schema__`"""
        if not is_dataclass(cls):
            raise TypeError(f"{cls.__name__} must be a dataclass")

        columns: list[BuilderColumn] = []
        constraints: dict[str, list[Constraint]] = {col: [] for col in cls.__annotations__} # pylint: disable=no-member
        _primary = None

        # Extract constraints from __schema__
        for constraint in cls.__schema__:  # pylint: disable=no-member
            target_col = constraint.column
            constraints[target_col].append(constraint)
            if isinstance(constraint, Primary) and _primary:
                raise ConstraintError("Cannot apply when a column has 2 primary keys")
            if isinstance(constraint, Primary):
                _primary = target_col
                continue

        # Process fields & constraints
        for field_def in fields(cls):  # Fetch fields using dataclass reflection
            field_name = field_def.name
            field_type = field_def.type
            col = TYPES.get(field_type, text)(field_name) # type: ignore

            # Check if there's a default value
            if field_def.default is not MISSING:
                default_value = field_def.default
                col = col.default(default_value)

            # Apply constraints dynamically
            for constraint in constraints.get(field_name, []):
                constraint.apply(col)

            columns.append(col)

        cls._primary = _primary
        cls._tbl = db.create_table(cls.__name__.lower(), columns)


    @classmethod
    def where(cls, **kwargs):
        """Basic select operation"""
        return QueryBuilder(cls).where(**kwargs)


    @classmethod
    def create(cls, **kwargs):
        """Create data based on kwargs"""
        cls._tbl.insert(kwargs)
        return cls(**kwargs)  # pylint: disable=not-callable


    def update(self, __primary=NULL, /, **kwargs):
        """Update current data"""
        # pylint: disable=protected-access
        primary = self._primary or __primary
        if primary is NULL:
            raise ValueError(
                "The table does not have any primary key, cannot update due to undefined selection"
            )
        self._tbl.update({primary: getattr(self, primary)}, kwargs)  # type: ignore
        return type(self)(**kwargs)


    def delete(self, __primary=NULL, /):
        """Delete current data"""
        # pylint: disable=protected-access
        primary = self._primary or __primary
        if primary is NULL:
            raise ValueError(
                "The table does not have any primary key, cannot delete due to undefined selection"
            )
        self._tbl.delete_one({primary: getattr(self, primary)})  # type: ignore


def model(db: Database):
    """Initiate Model API compatible classes. Requires target to be a dataclass,
    the app automatically injects dataclass if this isn't a dataclass"""

    def outer(cls: Type[T]) -> Type[T]:
        if not issubclass(cls, BaseModel):
            raise TypeError(f"Model {cls.__name__} is not subclass of BaseModel.")
        if not is_dataclass(cls):
            cls = dataclass(cls)
        cls.create_table(db)
        return cls

    return outer


__all__ = [
    "model",
    "BaseModel",
    "Unique",
    "Primary",
    "Foreign",
    "QueryBuilder",
]
