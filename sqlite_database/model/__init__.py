"""Models"""

# pylint: disable=unused-import,unused-argument,cyclic-import

from typing import Any, Callable, Protocol, Self, Type, cast

from .helpers import Constraint, Unique, Primary, Foreign, TYPES, Validators
from .query_builder import QueryBuilder
from .errors import ConstraintError
from ..database import Database, Table
from ..column import text, BuilderColumn

NULL = object()


class ModelProtocol(Protocol):
    # pylint: disable=too-many-arguments
    """Model Protocol"""
    __schema__: tuple[Constraint, ...] | None
    __validators__: tuple[Validators, ...] | None
    _primary: str
    _tbl: Table

    @classmethod
    def create_table(cls, db: Database):
        """Create database according to annotations and schema from `__schema__`"""

    @classmethod
    def where(cls, **kwargs):
        """Basic select operation"""

    @classmethod
    def create(cls, **kwargs) -> Self: # type: ignore
        """Create data based on kwargs"""

    def update(self, __primary=NULL, /, **kwargs) -> Self:  # type: ignore
        """Update current data"""

    def delete(self):
        """Delete current data"""


## Model functions


@classmethod
def create_table(cls, db: Database):
    """Create database according to annotations and schema from `__schema__`"""
    # pylint: disable=no-member
    columns: list[BuilderColumn] = []
    constraints: dict[str, list[Constraint]] = {col: [] for col in cls.__annotations__}
    _primary = None

    # Extract constraints from __schema__
    for constraint in cls.__schema__:
        target_col = constraint.column
        constraints[target_col].append(constraint)
        if isinstance(constraint, Primary) and _primary:
            raise ConstraintError("Cannot apply when a column has 2 primary key")
        if isinstance(constraint, Primary):
            _primary = target_col
            continue

    # Process fields & constraints
    for field, field_type in cls.__annotations__.items():
        # print(field, type(field), dir(field))
        col = TYPES.get(field_type, text)(field)

        # Check if there's a default value
        if field in cls._field_defaults:
            default_value = cls._field_defaults[field]
            col = col.default(default_value)


        # Apply constraints dynamically
        for constraint in constraints.get(field, []):
            constraint.apply(col)

        columns.append(col)

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


def update(self: ModelProtocol, __primary=NULL, /, **kwargs):
    """Update current data"""
    # pylint: disable=protected-access
    primary = self._primary or __primary
    if primary is NULL:
        raise ValueError(
            "The table does not have any primary key, cannot update due to undefined selection"
        )
    self._tbl.update({primary: getattr(self, primary)}, kwargs)  # type: ignore
    return type(self)(**kwargs)


def delete(self: ModelProtocol, __primary=NULL, /):
    """Delete current data"""
    # pylint: disable=protected-access
    primary = self._primary or __primary
    if primary is NULL:
        raise ValueError(
            "The table does not have any primary key, cannot delete due to undefined selection"
        )
    self._tbl.delete_one({primary: getattr(self, primary)})  # type: ignore


def model(
    db: Database,
) -> Callable[[Type[Any]], Type[ModelProtocol]]:
    """Create a Table-compatible Model type."""

    def outer(cls: Type[Any]) -> Type[ModelProtocol]:
        if not issubclass(cls, tuple) or not hasattr(cls, "_fields"):
            raise TypeError(f"{cls.__name__} must be a subclass of NamedTuple")

        print("REACHED HERE")
        cls.__schema__ = getattr(cls, "__schema__", ())  # type: ignore
        cls.__validators__ = getattr(cls, "__validators__", ())  # type: ignore

        cls.create_table = create_table  # type: ignore
        cls.create = create # type: ignore
        cls.where = where  # type: ignore
        cls.update = update  # type: ignore
        cls.delete = delete  # type: ignore
        cls.create_table(db) # type: ignore
        ModelProtocol.register(cls) # type: ignore
        return cast(Type[ModelProtocol], cls) # type: ignore

    return outer


__all__ = ["model", "ModelProtocol", "Unique", "Primary", "Foreign", "QueryBuilder"]
