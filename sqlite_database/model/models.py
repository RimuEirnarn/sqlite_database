"""Models"""
# pylint: disable=unused-import,unused-argument

from typing import Any, Literal, Protocol, Type, cast, overload

from .model_helpers import Constraint, Unique, Primary, Foreign, TYPES
from ..database import Database, Table
from ..table import _null
from ..functions import ParsedFn
from ..column import text, BuilderColumn
from ..query_builder import Condition
from ..typings import (
    Data,
    Orders,
    Queries,
    Query,
    _MasterQuery,
    OnlyColumn,
    SquashedSqueries,
    JustAColumn,
)

class ModelProtocol(Protocol):
    # pylint: disable=too-many-arguments
    """Model Protocol"""
    __schema__: tuple[Constraint]
    _tbl: Table

    @classmethod
    def create_table(cls, db: Database):
        """Create database according to annotations and schema from `__schema__`"""

    @overload
    def select(
        self,
        condition: Condition = None,
        only: OnlyColumn = "*",
        limit: int = 0,
        offset: int = 0,
        order: Orders | None = None,
        squash: Literal[False] = False,
    ) -> Queries:  # type: ignore
        pass

    @overload
    def select(
        self,
        condition: Condition = None,
        only: OnlyColumn = "*",
        limit: int = 0,
        offset: int = 0,
        order: Orders | None = None,
        squash: Literal[True] = True,
    ) -> SquashedSqueries:
        pass

    @overload
    def select(
        self,
        condition: Condition = None,
        only: ParsedFn = _null,
        limit: int = 0,
        offset: int = 0,
        order: Orders | None = None,
        squash: Literal[False] = False,
    ) -> Any:
        pass

    @overload
    def select(
        self,
        condition: Condition = None,
        only: JustAColumn = "_COLUMN",
        limit: int = 0,
        offset: int = 0,
        order: Orders | None = None,
        squash: Literal[False] = False,
    ) -> list[Any]:
        pass

## Model functions

@classmethod
def create_table(cls, db: Database):
    """Create database according to annotations and schema from `__schema__`"""
    # pylint: disable=no-member
    columns: list[BuilderColumn] = []
    constraints: dict[str, list[Constraint]] = {col: [] for col in cls.__annotations__}

    # Extract constraints from __schema__
    for constraint in cls.__schema__:
        target_col = constraint.column
        constraints[target_col].append(constraint)

    # Process fields & constraints
    for field, field_type in cls.__annotations__.items():
        col = TYPES.get(field_type, text)(field)

        # Check if there's a default value
        if hasattr(cls, field):
            default_value = getattr(cls, field)
            col = col.default(default_value)

        # Apply constraints dynamically
        for constraint in constraints.get(field, []):
            constraint.apply(col)

        columns.append(col)

    cls._tbl = db.create_table(cls.__name__.lower(), columns)

@classmethod
def select(cls, condition, only):
    """a"""

def model(cls: Type[Any], db: Database):
    """Create a Table-compatible Model type."""
    if not issubclass(cls, tuple) or not hasattr(cls, "_fields"):
        raise TypeError(f"{cls.__name__} must be a subclass of NamedTuple")

    cls.__schema__ = getattr(cls, "_schema__", ()) # type: ignore

    cls.create_table = create_table # type: ignore
    return cast(ModelProtocol, cls)
