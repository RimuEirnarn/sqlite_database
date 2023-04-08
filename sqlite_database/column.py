"""Column"""

from typing import Any, Self
from .locals import _PATH, SQLACTION, SQLITETYPES
from ._utils import check_one, matches
from .typings import null


class Column:  # pylint: disable=too-many-instance-attributes
    """Column

    tip: for foreign_ref, you can split with / to separate table and column name.
    e.g: user/id"""

    def __init__(self,  # pylint: disable=too-many-arguments
                 name: str,
                 type_: SQLITETYPES,
                 foreign: bool = False,
                 foreign_ref: str | None = None,
                 primary: bool = False,
                 unique: bool = False,
                 nullable: bool = True,
                 default: Any = None,
                 on_delete: SQLACTION = "cascade",
                 on_update:
                 SQLACTION = "cascade") -> None:
        self._name = check_one(name)
        self._type = check_one(type_)
        self._unique = unique
        self._nullable = nullable
        self._default = default
        self._foreign_enabled = foreign
        while foreign_ref:
            if not matches(_PATH, foreign_ref):
                raise ValueError(
                    "foreign_ref has no / separator to separate table and column.")
            ref = foreign_ref.split('/', 1)
            source = ref[0]
            scolumn = ref[1] if len(ref) == 2 else name
            self._source = source
            self._source_column = scolumn
            self._foreign = foreign_ref
            break

        if not foreign:
            self._foreign = None
            self._foreign_enabled = False
        self._update = on_update
        self._delete = on_delete
        self._is_primary = primary

    @property
    def name(self):
        """Column Name"""
        return self._name

    @property
    def unique(self):
        """Is unique"""
        return self._unique

    @property
    def default(self):
        """Default value"""
        return self._default

    @property
    def nullable(self):
        """Nullable"""
        return self._nullable

    @property
    def raw_source(self):
        """Source / Foreign Reference"""
        return self._foreign

    @property
    def foreign(self):
        """Is foreign enabled?"""
        return self._foreign_enabled

    @property
    def source(self):
        """Source / Foreign Reference"""
        if self._foreign is None:
            raise AttributeError("Source is unset")
        return self._source

    @property
    def source_column(self):
        """Source column / Foreign reference column"""
        if self._foreign is None:
            raise AttributeError("Source column is unset")
        return self._source_column

    @property
    def primary(self):
        """Is primary or not?"""
        return self._is_primary

    @property
    def on_update(self):
        """Update setting"""
        return self._update

    @property
    def on_delete(self):
        """Delete setting"""
        return self._delete

    @property
    def type(self):
        """Type"""
        return self._type

    def __repr__(self) -> str:
        return f"<{self.type.title()}{type(self).__name__} -> {self.name}>"

    def __eq__(self, __o: 'Column') -> bool:
        if not isinstance(__o, Column):
            raise NotImplementedError
        other = (__o.name, __o.type, __o.unique, __o.nullable, __o.default,
                 __o.primary, __o.raw_source, __o.on_delete, __o.on_update)
        self_ = (self.name, self.type, self.unique, self.nullable, self.default,
                 self.primary, self.raw_source, self.on_delete, self.on_update)
        return all((item1 in self_ for item1 in other))


class BuilderColumn:  # pylint: disable=too-many-instance-attributes
    """Builder Column -- Column Implementation using Builder Column"""

    def __init__(self) -> None:
        self._update: SQLACTION = "cascade"
        self._delete: SQLACTION = "cascade"
        self._primary = False
        self._default = None
        self._nullable = False
        self._unique = False
        self._type: SQLITETYPES = None  # type: ignore
        self._name = ""
        self._source = ""
        self._source_column = ""
        self._foreign = False

    def integer(self, name: str) -> Self:
        """Set as type integer"""
        self._name = name
        self._type = "integer"
        return self

    def text(self, name: str) -> Self:
        """Set as type text"""
        self._name = name
        self._type = 'text'
        return self

    def blob(self,  name: str) -> Self:
        """Set as type blob"""
        self._name = name
        self._type = 'blob'
        return self

    def real(self, name: str) -> Self:
        """Set as type real"""
        self._name = name
        self._type = 'real'
        return self

    def default(self, default_value: Any):
        """Set default value"""
        self._default = default_value
        return self

    def primary(self) -> Self:
        """Set primary"""
        self._primary = True
        self._unique = True
        return self

    def unique(self) -> Self:
        """Set unique"""
        self._unique = True
        return self

    def foreign(self, source: str) -> Self:
        """Set foreign reference"""
        if not "/" in source:
            raise ValueError("Foreign ref invalid")
        self._source, self._source_column = source.split('/', 1)
        self._foreign = True
        return self

    def on_update(self, action: SQLACTION):
        """Set on update action"""
        self._update = action
        return self

    def on_delete(self, action: SQLACTION):
        """Set on delete action"""
        self._delete = action
        return self

    def _column_challenge(self):
        if not self._name:
            raise ValueError("Name must be defined")
        if not self._type:
            raise ValueError("Type must be defined")
        if self._foreign:
            if not self._source or self._source_column:
                raise ValueError("One of foreign ref must present")
        if not self._nullable and self._default is null:
            raise ValueError("Cannot set from not null while default is null")

    def to_column(self):
        """Conver from BuilderColumn to Column"""
        return Column(self._name,
                      self._type,
                      self._foreign,
                      self._source+'/'+self._source_column,
                      self._primary,
                      self._unique,
                      self._nullable,
                      self._default,
                      self._delete,
                      self._update
                      )

    def __eq__(self, __o: 'Column') -> bool:
        return self.to_column() == __o


def text(name: str) -> BuilderColumn:
    """Create a text column with name"""
    return BuilderColumn().text(name)


def integer(name: str) -> BuilderColumn:
    """Create a integer column with name"""
    return BuilderColumn().integer(name)


def blob(name: str) -> BuilderColumn:
    """Create a blob column with name"""
    return BuilderColumn().blob(name)


def real(name: str) -> BuilderColumn:
    """Create a real column with name"""
    return BuilderColumn().real(name)


__all__ = ['Column', 'BuilderColumn', 'text', 'integer', 'blob', 'real']
