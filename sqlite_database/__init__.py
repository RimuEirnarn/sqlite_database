"""Database"""
#from atexit import register as atexit_register, unregister as atexit_register
from weakref import finalize
from sqlite3 import OperationalError, connect
from typing import Iterable, Optional

from ._utils import (WithCursor, check_iter, check_one, dict_factory, null,
                     sqlite_multithread_check, AttrDict)
from .column import BuilderColumn, Column, text, integer, blob, real
from .locals import this
from .query_builder import extract_table_creations
from .signature import op
from .table import Table
from .errors import DatabaseExistsError, DatabaseMissingError

## DEBUG IMPORT

#import inspect
#from ._debug import map_frame
#from memory_profiler import profile

Columns = Iterable[Column] | Iterable[BuilderColumn]

IGNORE_TABLE_CHECKS = (
    "sqlite_master", "sqlite_temp_schema", "sqlite_temp_master")


class Database:
    """Sqlite3 database, this provide basic integration."""

    _active: dict[str, "Database"] = {}

    def __new__(cls, path):
        if path in cls._active:
            return cls._active[path]
        self = object.__new__(cls)
        print('new object initiated')
        # self.__init__(path, **kwargs)
        if path != ":memory:":
            cls._active[path] = self
        return self

    def __init__(self, path: str, **kwargs) -> None:
        #trace = inspect.currentframe()
        print(f"object {self} is initiated!")
        #print(map_frame(trace))
        #if self.__dict__.get('traces', False) is False:
        #    self.traces = [trace]
        #else:
        #    self.traces.append(trace)
        if self.__dict__.get('_initiated', False) is False:
            kwargs['check_same_thread'] = sqlite_multithread_check() != 3
            self._path = path
            self._database = connect(path, **kwargs)
            self._database.row_factory = dict_factory
            self._closed = False
            self._table_instances: dict[str, Table] = {}
            # I'm not sure how to check if this 'self' is a copy or newly born object...
            finalize(self, self._finalise_close)
            self._initiated = True

    def _finalise_close(self):
        """Alias for .close()"""
        self.close()

    def cursor(self) -> WithCursor:
        """Create cursor"""
        return self._database.cursor(WithCursor)  # type: ignore

    # @profile
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

        with self._database as that:
            that.execute(query)
        table_ = self.table(table, columns)
        table_._deleted = False  # pylint: disable=protected-access
        self._table_instances[table] = table_
        return table_

    # @profile
    def delete_table(self, table: str):
        """Delete an existing table

        Args:
            table (str): table name
        """
        check_one(table)
        table_ = self.table(table)
        self._database.execute(f"drop table {table}")
        del self._table_instances[table]
        table_._delete_hook()  # pylint: disable=protected-access

    def table(self, table: str, __columns: Optional[Iterable[Column]] = None):
        """fetch table"""
        if self._table_instances.get(table, None) is not None:
            return self._table_instances[table]

        # Undefined behavior? Something else? idk.
        #if self.check_table(table) is False:
        #    raise DatabaseMissingError(f"table {table} doesn't exists.")

        this_table = Table(self, table, __columns)
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
        self._database.execute(f"alter table {old_table} rename to {new_table}")
        return self.table(new_table)

    def check_table(self, table: str):
        """Check if table is exists or not."""
        check_one(table)
        if table in IGNORE_TABLE_CHECKS:
            return True  # Let's return true.
        cursor = self._database.execute(
            "select name from sqlite_master where type='table' and name=?", (table,))
        if cursor.fetchone():
            return True
        return False

    def __repr__(self) -> str:
        return f"<Database {id(self)}>"

    def close(self):
        """Close database"""
        if self._closed: # Avoid multiple closes from same-reference object.
            # A memory tests has been dispatched; databases are closed when at interpreter exit
            # This causes a 'memory leaks', we must only manually add atexit once for
            # the same object.
            return
        self._database.close()
        #unregister(self.close)
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
