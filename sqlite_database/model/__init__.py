"""Models"""

# pylint: disable=unused-import,unused-argument,cyclic-import

from contextlib import contextmanager
from typing import Any, Callable, Self, Type, TypeVar, overload
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

VALID_HOOKS_NAME = (
    "before_create",
    "after_create",
    "before_update",
    "after_update",
    "before_delete",
    "after_delete",
)

## Model functions


class BaseModel:  # pylint: disable=too-few-public-methods,too-many-public-methods
    """Base class for all Models using Model API"""

    __table_name__ = ""
    __schema__: tuple[Constraint, ...] = ()
    __validators__: dict[str, list[Validators]] = {}
    __hooks__: "dict[str, list[Callable[[Self], None] | str]]" = {}
    __hidden__: tuple[str, ...] = ()
    _tbl: Table
    _primary: str | None

    @classmethod
    def create_table(cls, db: Database):
        """Create database according to annotations and schema from `__schema__`"""
        if not is_dataclass(cls):
            raise TypeError(f"{cls.__name__} must be a dataclass")

        columns: list[BuilderColumn] = []
        constraints: dict[str, list[Constraint]] = {
            col: [] for col in cls.__annotations__
        }  # pylint: disable=no-member
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
            col = TYPES.get(field_type, text)(field_name)  # type: ignore

            # Check if there's a default value
            if field_def.default is not MISSING:
                default_value = field_def.default
                col = col.default(default_value)

            # Apply constraints dynamically
            for constraint in constraints.get(field_name, []):
                constraint.apply(col)

            columns.append(col)

        cls._primary = _primary
        cls.__table_name__ = cls.__table_name__ or cls.__name__.lower()
        try:
            cls._tbl = db.create_table(cls.__table_name__, columns)
        except DatabaseExistsError:
            cls._tbl = db.table(cls.__table_name__.lower())

    @classmethod
    def _execute_hooks(cls, name: str, instance: Self):
        for hook in cls.__hooks__.get(name, ()):
            if isinstance(hook, str):
                getattr(cls, hook)(instance)
            else:
                hook(instance)

    @classmethod
    def _execute_validators(cls, name: str, instance: Self):
        for validator in cls.__validators__.get(name, ()):
            validator.validate(instance)

    @classmethod
    def _register(cls, type_: str = 'hook', name: str = "", if_fail: str = ""):
        """Register a hook/validator under a name"""
        if type_ not in ("hook", "validator"):
            raise ValueError("Which do you want?")
        def function(func):
            if name == '':
                raise ValueError(f"{type_.title()} name needs to be declared.")
            if type_ == 'hook':
                if name not in VALID_HOOKS_NAME:
                    raise ValueError("Name of a hook doesn't match with expected value")
                cls.__hooks__.setdefault(name, [])
                if cls.__hooks__[name]:
                    cls.__hooks__[name] = [func]
                else:
                    cls.__hooks__[name].append(func)
                return func

            if not is_dataclass(cls):
                raise TypeError("Dataclass is required for this class")

            fields_ = tuple((field.name for field in fields(cls)))
            if name not in fields_:
                raise ValueError("Expected validator to has name as column field")

            fail = if_fail or f"{name} fails certain validator"

            cls.__validators__.setdefault(name, [])
            validator = Validators(func, fail)
            if cls.__validators__[name]:
                cls.__validators__[name] = [validator]
            else:
                cls.__validators__[name].append(validator)
            return func
        return function

    @classmethod
    def create(cls, **kwargs):
        """Create data based on kwargs"""
        instance = cls(**kwargs)

        cls._execute_hooks("before_create", instance)
        for key in kwargs:
            cls._execute_validators(key, instance)
        cls._tbl.insert(kwargs)
        cls._execute_hooks("after_create", instance)
        return instance

    def update(self, __primary: str | object = NULL, /, **kwargs):
        """Update current data"""
        # pylint: disable=protected-access
        primary = self._primary or __primary
        if primary is NULL:
            raise ValueError(
                "The table does not have any primary key, cannot update due to undefined selection"
            )
        self._execute_hooks("before_update", self)
        for key in kwargs:
            self._execute_validators(key, self)
        self._tbl.update({primary: getattr(self, primary)}, kwargs)  # type: ignore
        for key, value in kwargs.items():
            setattr(self, key, value)
        self._execute_hooks("after_update", self)
        return self

    def delete(self, __primary=NULL, /):
        """Delete current data"""
        # pylint: disable=protected-access
        primary = self._primary or __primary
        if primary is NULL:
            raise ValueError(
                "The table does not have any primary key, cannot delete due to undefined selection"
            )
        self._execute_hooks("before_delete", self)
        self._tbl.delete_one({primary: getattr(self, primary)})  # type: ignore
        self._execute_hooks("after_delete", self)

    @classmethod
    def bulk_create(cls, records: list[dict]):
        """Insert multiple records at once."""
        cls._tbl.insert_many(records)
        return [cls(**record) for record in records]  # Return list of instances

    @classmethod
    def bulk_update(cls, records: list[dict], key: str | object = NULL):
        """Update multiple records using a primary key or provided key."""
        key_ = cls._primary or key
        if key is NULL:
            raise ValueError(
                "The table does not have any primary key, or key parameter is not provided"
            )
        for record in records:
            if key_ not in record:
                raise ValueError(f"Missing primary key '{key_}' in record: {record}")
            cls._tbl.update({key_: record[key_]}, record)  # type: ignore

    @classmethod
    def bulk_delete(cls, keys: list[Any], key: str):
        """Delete multiple records using a primary key."""
        cls._tbl.delete({key: in_(keys)})

    @classmethod
    def first(cls, **kwargs):
        """Return the first matching record or None if no match is found."""
        result = cls.where(**kwargs).limit(1).fetch_one()
        return result

    @classmethod
    def one(cls, **kwargs):
        """Return exactly one record. Raises error if multiple results exist."""
        results = cls.where(**kwargs).fetch()
        if len(results) > 1:
            raise ValueError(f"Expected one record, but found {len(results)}")
        return results[0] if results else None

    @classmethod
    def all(cls):
        """Return all values from the table"""
        return cls.where().fetch()

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
        if is_dataclass(self):  # always true, though, just in case
            instance = asdict(self)
            return {k: v for k, v in instance if k not in self.__hidden__}
        return {}

    def to_safe_instance(self):
        """Wrap instance that complies with __hidden__."""
        if is_dataclass(self):
            instance = {k: (v if not k in self.__hidden__ else None) for k, v in asdict(self)}
            return type(self)(**instance)
        raise TypeError("This class must be a dataclass")

    def raw(self, query: str, params: list[Any] | tuple[Any, ...] | dict[str, Any]):
        """Raw SQL query"""
        return self._tbl._sql.execute(query, params)  # pylint: disable=protected-access

    def has_many(self, related: "Type[T]", foreign_key: str | object = NULL):
        """Ensure related_model has a Foreign key pointing to self"""
        foreign_key = None

        if not self._primary:
            raise ConstraintError(
                f"The table {self.__table_name__} does not have any primary key "
                "required for has_many()"
            )

        # Scan __schema__ of related model to find a Foreign key linking back
        for constraint in related.__schema__:
            if isinstance(constraint, Foreign):
                table_ref, _ = constraint.target.split("/")
                if table_ref == self.__class__.__name__.lower():
                    foreign_key = constraint.column
                    break

        if not foreign_key:
            raise ValueError(
                f"{related.__name__} does not have a Foreign key pointing "
                f"to {self.__class__.__name__}"
            )

        # Perform the actual query
        return related.where(**{foreign_key: getattr(self, self._primary)}).fetch()

    def belongs_to(self, related_model: "Type[T]"):
        """Retrieve the related model that this instance belongs to."""
        # Find the Foreign() constraint that references `related_model`
        for constraint in self.__schema__:
            if isinstance(constraint, Foreign) and constraint.target.startswith(
                related_model.__table_name__ + "/"
            ):
                foreign_key = constraint.column
                referenced_column = constraint.target.split("/")[1]
                return related_model.where(
                    **{referenced_column: getattr(self, foreign_key)}
                ).fetch_one()

        raise ValueError(
            f"{self.__class__.__name__} does not belong to {related_model.__name__}"
        )

    def has_one(self, related_model: "Type[T]"):
        """Retrieve the related model where this instance is referenced."""
        # Find the Foreign() constraint in `related_model` that references this model
        for constraint in related_model.__schema__:
            if (
                isinstance(constraint, Foreign)
                and constraint.target == f"{self.__table_name__}/{self._primary}"
            ):
                foreign_key = constraint.column
                return related_model.where(**{foreign_key: self._primary}).fetch_one()

        raise ValueError(
            f"{related_model.__name__} does not have a one-to-one relationship "
            f"with {self.__class__.__name__}"
        )

    def hook(self, name: str):
        """Register a hook"""
        return self._register('hook', name)

    def validator(self, column_name: str, if_fail: str):
        """Register a validator"""
        return self._register("validator", column_name, if_fail)

    def get_table(self):
        """Return table instance"""
        return self._tbl

    def chunk(self, limit: int, callback: Callable[[list[Self]], None] | None = None):
        """Return specified instance by the amount of limit, or execute provided callback"""
        offset = 0
        while True:
            batch = self.query().limit(limit).offset(offset).fetch()

            if not batch:
                break

            if callback:
                callback(batch)
            else:
                yield batch

            if len(batch) != limit:
                break

    @classmethod
    def where(cls, **kwargs):
        """Basic select operation"""
        return QueryBuilder(cls).where(**kwargs)

    @classmethod
    def query(cls):
        """Return Query Builder related to this model"""
        return QueryBuilder(cls)

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
