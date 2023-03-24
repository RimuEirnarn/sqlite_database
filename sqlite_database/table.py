"""Table"""

from sqlite3 import OperationalError
from typing import Any, Iterable, NamedTuple, Optional, Type

from ._utils import WithCursor, check_iter, check_one
from .column import BuilderColumn, Column
from .errors import TableRemovedError, UnexpectedResultError
from .locals import SQLITEPYTYPES
from .query_builder import (build_update_data, combine_keyvals,
                            extract_signature, extract_single_column,
                            fetch_columns, format_paramable)
from .signature import op
from .typings import Condition, Data, Orders, Queries, Query, _MasterQuery, TypicalNamedTuple

# Let's add a little bit of 'black' magic here.


@classmethod
def get_table(cls):
    """Get table"""
    return getattr(cls, '_table', None)


class Table:
    """Table. Make sure you remember how the table goes."""

    _ns: dict[str, Type[NamedTuple]] = {}

    def __init__(self,
                 parent: 'Database',  # type: ignore
                 table: str,
                 __columns: Optional[Iterable[Column]] = None) -> None:
        self._parent = parent
        self._deleted = False
        self._table = check_one(table)
        self._columns: Optional[list[Column]] = list(
            __columns) if __columns else None

        if self._columns is None and table != "sqlite_master":
            self._fetch_columns()

    def _delete_hook(self):
        try:
            self.select()
        except OperationalError:
            self._deleted = True

    def _fetch_columns(self):
        table = self._table
        try:
            master = self._parent.table("sqlite_master")
            tabl = master.select_one(
                {"type": op == "table", "name": op == table})
            if tabl is None:
                raise ValueError("What the hell?")
            cols = fetch_columns(_MasterQuery(**tabl))
            self._columns = cols
            return 0
        except Exception:  # pylint: disable=broad-except
            return 1

    def _raw_exec(self, query: str, data: dict[str, Any]) -> WithCursor:
        """No thread safe :("""
        cursor = self._parent.cursor()
        cursor.execute(query, data)
        return cursor

    def _mksquery(self,
                  filter_: Condition = None,
                  limit: int = 0,
                  order: Optional[Orders] = None):
        cond, data = extract_signature(filter_)
        query = f"select * from {self._table}{' '+cond if cond else ''}"
        if limit:
            query += f" limit {limit}"
        if order:
            query += " order by"
            for ord_, order_by in order.items():
                query += f" {ord_} {order_by},"
            query = query[:-1]
        # print(query, data)
        return query, data

    def _mkuquery(self,
                  new_data: Data,
                  filter_: Condition = None,
                  limit: int = 0,
                  order: Optional[Orders] = None):
        cond, data = extract_signature(filter_)
        new_str, updated = build_update_data(new_data)
        query = f"update {self._table} set {new_str} {cond}"
        if limit:
            query += f" limit {limit}"
        if order:
            query += " order by"
            for ord_, order_by in order.items():
                query += f" {ord_} {order_by},"
            query = query[:-1]
        # print(query, data | _combine_keyvals(updated, new_data))
        return query, data | combine_keyvals(updated, new_data)

    def _mkdquery(self,
                  filter_: Condition = None,
                  limit: int = 0,
                  order: Optional[Orders] = None):
        cond, data = extract_signature(filter_)
        query = f"delete from {self._table} {cond}"
        if limit:
            query += f" limit {limit}"
        if order:
            query += " order by"
            for ord_, order_by in order.items():
                query += f" {ord_} {order_by}"
            query = query[:-1]
        # print(query, data)
        return query, data

    def _mkiquery(self, data: Data):
        converged = format_paramable(data)
        query = f"insert into {self._table} ({', '.join(val for val in converged)}) \
values ({', '.join(val for _,val in converged.items())})"
        # print(query, data)
        return query, data

    def _control(self):
        if self._deleted:
            raise TableRemovedError(f"{self._table} is already removed")
        if self._parent.closed:
            raise ConnectionError("Connection to database was closed.\
 A operation was held but database is already closed.")

    def force_nodelete(self):
        """Force "undelete" table. Used if table was mistakenly assigned as
        deleted."""
        self._deleted = True

    def delete(self, filter_: Condition = None, limit: int = 0, order: Optional[Orders] = None):
        """Delete row or rows

        Args:
            filter_ (Condition, optional): Condition to determine deletion
            See `Signature` class about conditional stuff. Defaults to None.
            limit (int, optional): Limit deletion by integer. Defaults to 0.
            order (Optional[Orders], optional): Order of deletion. Defaults to None.

        Returns:
            int: Rows affected
        """
        query, data = self._mkdquery(filter_, limit, order)
        self._control()
        cursor = self._parent.sql.execute(query, data)
        rcount = cursor.rowcount
        self._parent.sql.commit()
        return rcount

    def delete_one(self, filter_: Condition = None, order: Optional[Orders] = None):
        """Delete a row

        Args:
            filter_ (Condition, optional): Conditional to determine deletion.
            Defaults to None.
            order (Optional[Orders], optional): Order of deletion. Defaults to None.
        """
        return self.delete(filter_, 1, order)

    def insert(self, data: Data):
        """Insert data to current table

        Args:
            data (Data): Data to insert. Make sure it's compatible with the table.

        Returns:
            int: Last rowid
        """
        query, _ = self._mkiquery(data)
        self._control()
        cursor = self._parent.sql.execute(query, data)
        rlastrowid = cursor.lastrowid
        self._parent.sql.commit()
        return rlastrowid

    def insert_multiple(self, datas: Iterable[Data]):
        """Insert multiple values

        Args:
            datas (Iterable[Data]): Data to be inserted.
        """
        for data in datas:
            self.insert(data)

    def insert_many(self, datas: Iterable[Data]):
        """Alias to `insert_multiple`"""
        return self.insert_multiple(datas)

    def update(self,
               new_data: Data,
               filter_: Condition = None,
               limit: int = 0,
               order: Optional[Orders] = None):
        """Update rows of current table

        Args:
            new_data (Data): New data to update
            filter_ (Condition, optional): Condition dictionary
            See `Signature` about how filter_ works. Defaults to None.
            limit (int, optional): Limit updates. Defaults to 0.
            order (Optional[Orders], optional): Order of change. Defaults to None.

        Returns:
            int: Rows affected
        """
        query, data = self._mkuquery(new_data, filter_, limit, order)
        self._control()
        cursor = self._parent.sql.execute(query, data)
        rcount = cursor.rowcount
        self._parent.sql.commit()
        return rcount

    def update_one(self,
                   new_data: Data,
                   filter_: Condition | None,
                   order: Orders | None = None) -> int:
        """Update 1 data only"""
        return self.update(new_data, filter_, 1, order)

    def select(self,
               filter_: Condition = None,
               limit: int = 0,
               order: Optional[Orders] = None) -> Queries:
        """Select data in current table. Bare .select() returns all data.

        Args:
            filter_ (Condition, optional): Conditions to used. Defaults to None.
            limit (int, optional): Limit of select. Defaults to 0.
            order (Optional[Orders], optional): Selection order. Defaults to None.

        Returns:
            Queries: Selected data
        """
        self._control()
        query, data = self._mksquery(filter_, limit, order)
        with self._parent.sql:
            return self._parent.sql.execute(query, data).fetchall()

    def select_one(self,
                   filter_: Condition = None,
                   order: Optional[Orders] = None) -> Query | None:
        """Select one data

        Args:
            filter_ (Condition, optional): Condition to use. Defaults to None.
            order (Optional[Orders], optional): Order of selection. Defaults to None.

        Returns:
            Query: Selected data
        """
        self._control()
        query, data = self._mksquery(filter_, 1, order)
        with self._parent.sql:
            return self._parent.sql.execute(query, data).fetchone()

    def exists(self, filter_: Condition = None):
        """Check if data is exists or not.

        Args:
            filter_ (Condition, optional): Condition to use. Defaults to None.
        """
        data = self.select_one(filter_)
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
        sql = self._parent.sql
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
        self._parent.sql.execute(query)

    def __repr__(self) -> str:
        return f"<Table({self._table}) -> {self._parent}>"
