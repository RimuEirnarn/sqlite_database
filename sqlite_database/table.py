"""Table"""

from sqlite3 import Connection, OperationalError
from typing import Any, Generator, Iterable, NamedTuple, Optional, Type

import weakref

from ._utils import AttrDict, check_iter, check_one
from .column import BuilderColumn, Column
from .errors import TableRemovedError, UnexpectedResultError
from .locals import SQLITEPYTYPES
from .query_builder import (Condition, extract_single_column,
                            fetch_columns, build_select,
                            build_insert, build_delete,
                            build_update)
from .signature import op
from .typings import (Data, Orders, Queries, Query, TypicalNamedTuple,
                      _MasterQuery, OnlyColumn)
from .config import Config

# Let's add a little bit of 'black' magic here.


@classmethod
def get_table(cls):  # pylint: disable=missing-function-docstring
    return getattr(cls, '_table', None)


class Table:
    """Table. Make sure you remember how the table goes."""

    _ns: dict[str, Type[NamedTuple]] = {}

    def __init__(self,
                 parent,  # type: ignore
                 table: str,
                 db_config: Config | None = None,
                 __columns: Optional[Iterable[Column]] = None) -> None:
        self._parent_repr = repr(parent)
        self._sqlitemaster = None
        self._sql: Connection = parent.sql
        self._deleted = False
        self._table = check_one(table)
        self._config = Config(crunch=False) if db_config is None else db_config
        self._columns: Optional[list[Column]] = list(
            __columns) if __columns else None
        weakref.finalize(self, self._finalize)

        if self._columns is None and table != "sqlite_master":
            self._fetch_columns(parent)

    def _finalize(self):
        pass

    def _delete_hook(self):
        try:
            self.select()
        except OperationalError:
            self._deleted = True

    def _fetch_columns(self, parent=None):
        table = self._table
        try:
            if not self._sqlitemaster and parent is not None:
                master = parent.table("sqlite_master")
                self._sqlitemaster = master
            else:
                master: 'Table' = self._sqlitemaster  # type: ignore
            tabl = master.select_one(
                {"type": op == "table", "name": op == table})
            if tabl is None:
                raise ValueError("What the hell?")
            cols = fetch_columns(_MasterQuery(**tabl))
            self._columns = cols
            return 0
        except Exception:  # pylint: disable=broad-except
            return 1

    def _raw_exec(self, query: str, data: dict[str, Any]):
        """No thread safe :("""
        cursor = self._sql.cursor()
        cursor.execute(query, data)
        return cursor

    @staticmethod
    def _crunch(query: Queries):
        data: dict[str, list[Any]] = AttrDict()
        for value in query:
            for key, val in value.items():
                if key not in data:
                    data[key] = []
                data[key].append(val)
        return data

    def _control(self):
        if self._deleted:
            raise TableRemovedError(f"{self._table} is already removed")

    def force_nodelete(self):
        """Force "undelete" table. Used if table was mistakenly assigned as
        deleted."""
        self._deleted = True

    def delete(self, condition: Condition = None, limit: int = 0, order: Optional[Orders] = None):
        """Delete row or rows

        Args:
            condition (Condition, optional): Condition to determine deletion
                See `Signature` class about conditional stuff. Defaults to None.
            limit (int, optional): Limit deletion by integer. Defaults to 0.
            order (Optional[Orders], optional): Order of deletion. Defaults to None.

        Returns:
            int: Rows affected
        """
        query, data = build_delete(
            self._table, condition, limit, order)  # type: ignore
        self._control()
        cursor = self._sql.execute(query, data)
        rcount = cursor.rowcount
        self._sql.commit()
        return rcount

    def delete_one(self, condition: Condition = None, order: Optional[Orders] = None):
        """Delete a row

        Args:
            condition (Condition, optional): Conditional to determine deletion.
            Defaults to None.
            order (Optional[Orders], optional): Order of deletion. Defaults to None.
        """
        return self.delete(condition, 1, order)

    def insert(self, data: Data):
        """Insert data to current table

        Args:
            data (Data): Data to insert. Make sure it's compatible with the table.

        Returns:
            int: Last rowid
        """
        query, _ = build_insert(self._table, data)  # type: ignore
        self._control()
        cursor = self._sql.execute(query, data)
        rlastrowid = cursor.lastrowid
        self._sql.commit()
        return rlastrowid

    def insert_multiple(self, datas: list[Data]):
        """Insert multiple values

        Args:
            datas (Iterable[Data]): Data to be inserted.
        """
        self._control()
        query, _ = build_insert(self._table, datas[0])  # type: ignore
        self._sql.executemany(query, datas)
        self._sql.commit()

    def insert_many(self, datas: list[Data]):
        """Alias to `insert_multiple`"""
        return self.insert_multiple(datas)

    def update(self,
               condition: Condition | None = None,
               data: Data | None = None,
               limit: int = 0,
               order: Optional[Orders] = None):
        """Update rows of current table

        Args:
            data (Data): New data to update
            condition (Condition, optional): Condition dictionary. 
                See `Signature` about how condition works. Defaults to None.
            limit (int, optional): Limit updates. Defaults to 0.
            order (Optional[Orders], optional): Order of change. Defaults to None.

        Returns:
            int: Rows affected
        """
        if data is None:
            raise ValueError("data parameter must not be None")
        query, data = build_update(
            self._table, data, condition, limit, order)  # type: ignore
        self._control()
        cursor = self._sql.execute(query, data)
        rcount = cursor.rowcount
        self._sql.commit()
        return rcount

    def update_one(self,
                   condition: Condition | None = None,
                   new_data: Data | None = None,
                   order: Orders | None = None) -> int:
        """Update 1 data only"""
        return self.update(condition, new_data, 1, order)

    def select(self, # pylint: disable=too-many-arguments
               condition: Condition = None,
               only: tuple[str, ...] | None = None,
               limit: int = 0,
               offset: int = 0,
               order: Optional[Orders] = None) -> Queries:
        """Select data in current table. Bare .select() returns all data.

        Args:
            condition (Condition, optional): Conditions to used. Defaults to None.
            only: (OnlyColumn, optional): Select what you want. Default to None.
            limit (int, optional): Limit of select. Defaults to 0.
            offset (int, optional): Offset. Defaults to 0
            order (Optional[Orders], optional): Selection order. Defaults to None.

        Returns:
            Queries: Selected data
        """
        self._control()
        query, data = build_select(self._table,
                                   condition,
                                   only,
                                   limit,
                                   offset,
                                   order)  # type: ignore
        with self._sql:
            return self._sql.execute(query, data).fetchall()

    def paginate_select(self,
                        condition: Condition = None,
                        only: OnlyColumn = None,
                        length: int = 10,
                        order: Optional[Orders] = None) -> Generator[Queries, None, None]:
        """Paginate select

        Args:
            condition (Condition, optional): Confitions to use. Defaults to None.
            only: (OnlyColumn, optional): Select what you want. Default to None.
            length (int, optional): Pagination length. Defaults to 10.
            order (Optional[Orders], optional): Order. Defaults to None.

        Yields:
            Generator[Queries, None, None]: Step-by-step paginated result.
        """
        self._control()
        start = 0
        while True:
            query, data = build_select(self._table,
                                       condition,
                                       only,
                                       length,
                                       start,
                                       order)  # type: ignore
            with self._sql:
                fetched: list[AttrDict] = self._sql.execute(
                    query, data).fetchmany(length)
                if len(fetched) == 0:
                    return
                if len(fetched) != length:
                    yield fetched
                    return
                yield fetched
                start += length

    def select_one(self,
                   condition: Condition = None,
                   only: OnlyColumn = None,
                   order: Optional[Orders] = None) -> Query | None:
        """Select one data

        Args:
            condition (Condition, optional): Condition to use. Defaults to None.
            only: (OnlyColumn, optional): Select what you want. Default to None.
            order (Optional[Orders], optional): Order of selection. Defaults to None.

        Returns:
            Query: Selected data
        """
        self._control()
        query, data = build_select(
            self._table, condition, only, 1, 0, order)  # type: ignore
        with self._sql:
            return self._sql.execute(query, data).fetchone()

    def exists(self, condition: Condition = None):
        """Check if data is exists or not.

        Args:
            condition (Condition, optional): Condition to use. Defaults to None.
        """
        data = self.select_one(condition)
        if data is None:
            return False
        return True

    def get_namespace(self) -> Type[TypicalNamedTuple]:
        """Generate or return pre-existed namespace/table."""
        if self._ns.get(self._table, None):
            return self._ns[self._table]
        self._control()
        if self._columns:
            datatypes = {
                col.name: SQLITEPYTYPES[col.type] for col in self._columns}
            namespace_name = self._table.title()+"Table"
            namedtupled = NamedTuple(namespace_name, **datatypes)
            setattr(namedtupled, "_table", self)
            self._ns[self._table] = namedtupled
            return namedtupled
        self._fetch_columns()
        if self._columns is None:
            raise ExceptionGroup(f"Column misbehave. Table {self._table}", [
                ValueError("Mismatched columns"),
                UnexpectedResultError(
                    "._fetch_columns() does not change columns.")
            ])
        datatypes = {}
        for column in self._columns:
            datatypes[column.name] = SQLITEPYTYPES[column.type]
        namedtupled = NamedTuple(self._table.title()+"Table", **datatypes)

        self._ns[self._table] = namedtupled
        return namedtupled

    @property
    def columns(self):
        """Table columns"""
        if self._columns is None:
            raise AttributeError("columns is undefined.")
        return tuple(self._columns)

    @property
    def deleted(self):
        """Is table deleted"""
        return self._deleted

    @property
    def name(self):
        """Table name"""
        return self._table

    def add_column(self, column: Column | BuilderColumn):
        """Add column to table"""
        sql = self._sql
        column = column.to_column() if isinstance(column, BuilderColumn) else column
        if column.primary or column.unique:
            raise OperationalError(
                "New column cannot have primary or unique constraint")
        if column.nullable is False and column.default is None:
            raise OperationalError("New column cannot be not null while default value is \
set to null")
        if column.default is not None and column.foreign:
            raise OperationalError("New column must accept null default value if foreign \
constraint is enabled.")
        query = f"alter table {self._table} add column {extract_single_column(column)}"
        if self._columns is not None:
            self._columns.append(column)
        sql.execute(query)

    def rename_column(self, old_column: str, new_column: str):
        """Rename existing column to new column"""
        check_iter((old_column, new_column))
        query = f"alter table {self._table} rename column {old_column} to {new_column}"
        self._sql.execute(query)

    def __repr__(self) -> str:
        return f"<Table({self._table}) -> {self._parent_repr}>"


__all__ = ['Table']
