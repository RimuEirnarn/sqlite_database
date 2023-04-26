"""Database"""
from atexit import register as atexit_register
from weakref import finalize, WeakValueDictionary
from sqlite3 import OperationalError, connect
from typing import Iterable, Optional, Mapping

from ._utils import (WithCursor, check_iter, check_one, dict_factory, null,
                     sqlite_multithread_check, AttrDict)
from .column import BuilderColumn, Column, text, integer, blob, real
from .locals import this
from .query_builder import extract_table_creations
from .signature import op
from .table import Table
from .errors import DatabaseExistsError, DatabaseMissingError
Columns = Iterable[Column] | Iterable[BuilderColumn]

IGNORE_TABLE_CHECKS = (
    "sqlite_master", "sqlite_temp_schema", "sqlite_temp_master")


class Database:
    """Sqlite3 database, this provide basic integration."""

    _active: Mapping[str, "Database"] = WeakValueDictionary()

    def __new__(cls, path: str, **kwargs): # pylint: disable=unused-argument
        if path in cls._active:
            return cls._active[path]
        self = object.__new__(cls)
        if path != ":memory:":
            cls._active[str(path)] = self
        return self

    def __init__(self, path: str, **kwargs) -> None:
        kwargs['check_same_thread'] = sqlite_multithread_check() != 3
        self._path = path
        self._database = connect(path, **kwargs)
        self._database.row_factory = dict_factory
        self._closed = False
        self._table_instances: dict[str, Table] = {}
        if not self._closed or self.__dict__.get("_initiated", False) is False:
            self._finalizer_fn = finalize(self, self.close)
            self._initiated = True

    def _finalizer(self):
        self.close()

    def cursor(self) -> WithCursor:
        """Create cursor"""
        return self._database.cursor(WithCursor)  # type: ignore

    def create_table(self, table: str, columns: Columns):
        """Create table

        Args:
            table (str): Table name
            columns (Iterable[Column]): Columns for table

        Returns:
            Table: Newly created table
        """
        columns = (column.to_column() if isinstance(
            column, BuilderColumn) else column for column in columns)
        tbquery = extract_table_creations(columns)
        query = f"create table {table} ({tbquery})"

        try:
            self._database.execute(query)
            self._database.commit()
        except OperationalError as error:
            raise DatabaseExistsError(f"table {table} already exists.") from error
        table_ = self.table(table, columns)
        table_._deleted = False  # pylint: disable=protected-access
        self._table_instances[table] = table_
        return table_

    def delete_table(self, table: str):
        """Delete an existing table

        Args:
            table (str): table name
        """
        check_one(table)
        table_ = self.table(table)
        self._database.execute(f"drop table {table}")
        # pylint: disable-next=protected-access
        del self._table_instances[table]
        table_._delete_hook()  # pylint: disable=protected-access

    def table(self, table: str, __columns: Optional[Iterable[Column]] = None):
        """fetch table"""
        if self._table_instances.get(table, None) is not None:
            return self._table_instances[table]

        try:
            this_table = Table(self, table, __columns)
        except OperationalError as exc:
            raise DatabaseMissingError(f"table {table} does not exists") from exc
        self._table_instances[table] = this_table
        return this_table

    def reset_table(self, table: str, columns: Columns) -> Table:
        """Reset existing table with new, this rewrote entire table than altering it."""
        try:
            self.delete_table(table)
        except OperationalError:
            pass
        return self.create_table(table, columns)

    def rename_table(self, old_table: str, new_table: str) -> Table:
        """Rename existing table to a new one."""
        check_iter((old_table, new_table))
        self.sql.execute(f"alter table {old_table} rename to {new_table}")
        self.sql.commit()
        return self.table(new_table)

    def check_table(self, table: str):
        """Check if table is exists or not."""
        check_one(table)
        if table in IGNORE_TABLE_CHECKS:
            return True  # Let's return true.
        cursor = self.sql.execute(
            "select name from sqlite_master where type='table' and name=?", (table,))
        if cursor.fetchone():
            return True
        return False

    def __repr__(self) -> str:
        return f"<Database {id(self)}>"

    def close(self):
        """Close database"""
        if self._closed:
            return
        self._database.close()
        if self.path == ":memory:":
            self._closed = True
            return
        if self.path in self._active:
            del type(self)._active[self.path]
        self._closed = True

    @property
    def tables(self) -> tuple[Table, ...]:
        """Return tuple containing all table except internal tables"""
        master = self.table("sqlite_master")
        listed = []
        for table in master.select():
            if table.type == "table":
                listed.append(self.table(table.name))
        return tuple(listed)

    @property
    def closed(self):
        """Is database closed?"""
        return self._closed

    @closed.setter
    def closed(self, __o: bool):
        """Is database closed?"""
        if __o:
            self.close()
            return
        raise ValueError("Expected non-false/non-null value")

    @property
    def path(self):
        """Path to SQL Connection"""
        return self._path or ":memory:"

    @property
    def sql(self):
        """SQL Connection"""
        return self._database


__version__ = "0.1.3.1"
__all__ = ["Database", "Table", "op",
           "Column", "null", 'AttrDict', 'text', 'integer', 'real', 'blob']
