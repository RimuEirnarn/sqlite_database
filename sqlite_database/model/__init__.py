"""Models"""

# pylint: disable=unused-import,unused-argument,cyclic-import

from contextlib import contextmanager
from typing import Any, Type, TypeVar
from dataclasses import asdict, dataclass, fields, is_dataclass, MISSING

from .helpers import Constraint, Unique, Primary, Foreign, TYPES, Validators
from .query_builder import QueryBuilder
from .errors import ConstraintError
from ..errors import DatabaseExistsError
from ..database import Database, Table
from ..column import text, BuilderColumn
from ..operators import in_

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
        try:
            cls._tbl = db.create_table(cls.__name__.lower(), columns)
        except DatabaseExistsError:
            cls._tbl = db.table(cls.__name__.lower())


    @classmethod
    def where(cls, **kwargs):
        """Basic select operation"""
        return QueryBuilder(cls).where(**kwargs)


    @classmethod
    def create(cls, **kwargs):
        """Create data based on kwargs"""
        cls._tbl.insert(kwargs)
        return cls(**kwargs)  # pylint: disable=not-callable


    def update(self, __primary: str | object =NULL, /, **kwargs):
        """Update current data"""
        # pylint: disable=protected-access
        primary = self._primary or __primary
        if primary is NULL:
            raise ValueError(
                "The table does not have any primary key, cannot update due to undefined selection"
            )
        self._tbl.update({primary: getattr(self, primary)}, kwargs)  # type: ignore
        for key, value in kwargs.items():
            setattr(self, key, value)
        return self


    def delete(self, __primary=NULL, /):
        """Delete current data"""
        # pylint: disable=protected-access
        primary = self._primary or __primary
        if primary is NULL:
            raise ValueError(
                "The table does not have any primary key, cannot delete due to undefined selection"
            )
        self._tbl.delete_one({primary: getattr(self, primary)})  # type: ignore

    @classmethod
    def bulk_create(cls, records: list[dict]):
        """Insert multiple records at once."""
        cls._tbl.insert_many(records)
        return [cls(**record) for record in records]  # Return list of instances

    @classmethod
    def bulk_update(cls, records: list[dict], key: str | object=NULL):
        """Update multiple records using a primary key or provided key."""
        key_ = cls._primary or key
        if key is NULL:
            raise ValueError(
                "The table does not have any primary key, or key parameter is not provided"
            )
        for record in records:
            if key_ not in record:
                raise ValueError(f"Missing primary key '{key_}' in record: {record}")
            cls._tbl.update({key_: record[key_]}, record) # type: ignore

    @classmethod
    def bulk_delete(cls, keys: list[Any], key: str):
        """Delete multiple records using a primary key."""
        cls._tbl.delete({key: in_(keys)})

    @classmethod
    def first(cls, **kwargs):
        """Return the first matching record or None if no match is found."""
        result = cls.where(**kwargs).limit(1).fetch_one()
        return cls(**result) if result else None

    @classmethod
    def one(cls, **kwargs):
        """Return exactly one record. Raises error if multiple results exist."""
        results = cls.where(**kwargs).fetch()
        if len(results) > 1:
            raise ValueError(f"Expected one record, but found {len(results)}")
        return cls(**results[0]) if results else None

    @classmethod
    def count(cls, **kwargs) -> int:
        """Return count of matching records."""
        return cls.where(**kwargs).count()

    @classmethod
    def exists(cls, **kwargs) -> bool:
        """Check if any record matches the query."""
        return cls.where(**kwargs).limit(1).fetch_one() is not None

    @classmethod
    @contextmanager
    def atomic(cls):
        """Perform operations within a transaction."""
        with cls._tbl:  # Assuming `transaction()` exists
            yield

    @classmethod
    def upsert(cls, key: str, **kwargs):
        """Insert or update a record based on primary key."""
        existing = cls.where(**{key: kwargs[key]}).fetch_one()
        if existing:
            return existing.update(**kwargs)
        return cls.create(**kwargs)

    def to_dict(self):
        """Convert model instance to dictionary."""
        if is_dataclass(self): # always true, though, just in case
            return asdict(self)
        return {}

    def raw(self, query: str, params: list[Any] | tuple[Any, ...] | dict[str, Any]):
        """Raw SQL query"""
        return self._tbl._sql.execute(query, params) # pylint: disable=protected-access


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
