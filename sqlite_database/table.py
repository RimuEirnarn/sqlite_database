"""Table"""

# pylint: disable=too-many-arguments,too-many-public-methods

from sqlite3 import Connection, OperationalError
from typing import (
    Any,
    Generator,
    Iterable,
    Literal,
    NamedTuple,
    Optional,
    Type,
    overload,
)

import weakref

from sqlite_database.functions import ParsedFn, Function, count


from .utils import crunch
from ._utils import check_iter, check_one, Row
from .column import BuilderColumn, Column
from .errors import TableRemovedError
from .query_builder import (
    Condition,
    extract_single_column,
    fetch_columns,
    build_select,
    build_insert,
    build_delete,
    build_update,
)
from .signature import op
from .typings import (
    Data,
    Orders,
    Queries,
    Query,
    _MasterQuery,
    OnlyColumn,
    SquashedSqueries,
    JustAColumn,
)

# Let's add a little bit of 'black' magic here.
_null = Function("__NULL__")()

class Table: # pylint: disable=too-many-instance-attributes
    """Table. Make sure you remember how the table goes."""

    _ns: dict[str, Type[NamedTuple]] = {}

    def __init__(
        self,
        parent,  # type: ignore
        table: str,
        __columns: Optional[Iterable[Column]] = None,  # type: ignore
    ) -> None:
        if parent.closed:
            raise ConnectionError("Connection to database is already closed.")
        self._parent_repr = repr(parent)
        self._sql: Connection = parent.sql
        # pylint: disable-next=protected-access
        self._sql_path = parent._path
        self._deleted = False
        self._force_dirty = False
        self._dirty = False
        self._auto = True
        self._table = check_one(table)
        self._prev_autocommit = None
        self._prev_auto = True
        self._columns: Optional[list[Column]] = list(__columns) if __columns else None
        weakref.finalize(self, self._finalize)

        if self._columns is None and table != "sqlite_master":
            self._fetch_columns()

    def __enter__(self):
        self._prev_auto = self._auto
        self._prev_autocommit = self._sql.isolation_level

        self._sql.isolation_level = None
        self._auto = False
        self._sql.execute("BEGIN TRANSACTION")
        return self

    def __exit__(self, exc_type, _, __):
        if exc_type is None:
            self._sql.commit()
        else:
            self._sql.rollback()
        self._sql.isolation_level = self._prev_autocommit
        self._auto = self._prev_auto

    @property
    def deleted(self):
        """Is table deleted"""
        return self._deleted

    @property
    def name(self):
        """Table name"""
        return self._table

    @property
    def force_dirty(self):
        """Force dirty state, whether .selecting() on dirty/uncommitted data is allowed or not"""
        return self._force_dirty

    @force_dirty.setter
    def force_dirty(self, value: bool):
        """Force dirty state, whether .selecting() on dirty/uncommitted data is allowed or not"""
        if not isinstance(value, bool):
            return
        self._force_dirty = value

    @property
    def auto_commit(self):
        """Auto commit state of this instance"""
        return self._auto

    @auto_commit.setter
    def auto_commit(self, value: bool):
        if not isinstance(value, bool):
            return
        self._auto = value

    @property
    def in_transaction(self):
        """Returns True if the table is in an active transaction."""
        return not self._auto or self._sql.isolation_level is None

    def _finalize(self):
        pass

    def _delete_hook(self):
        try:
            self.select()
        except OperationalError:
            self._deleted = True

    def _fetch_columns(self):
        table = self._table
        try:
            query, data = build_select(
                "sqlite_master", {"type": op == "table", "name": op == table}
            )
            cursor = self._sql.cursor()
            cursor.execute(query, data)
            tabl = cursor.fetchone()
            if tabl is None:
                raise ValueError("What the hell?")
            cols = fetch_columns(_MasterQuery(**tabl))
            self._columns = cols
            return 0
        except Exception:  # pylint: disable=broad-except
            return 1

    def _exec(
        self,
        query: str,
        data: dict[str, Any] | list[dict[str, Any]],
        which: Literal["execute", "executemany"] = "execute",
    ):
        """Execute a sql query"""
        cursor = self._sql.cursor()
        fn = cursor.execute if which == "execute" else cursor.executemany
        try:
            fn(query, data)
        except OperationalError as exc:
            exc.add_note(f"SQL query: {query}")
            exc.add_note(
                f"There's about {1 if isinstance(data, dict) else len(data)} value(s) inserted"
            )
            raise exc
        return cursor

    def _control(self):
        if self._deleted:
            raise TableRemovedError(f"{self._table} is already removed")

    def _query_control(self):
        if self._dirty and self._force_dirty is False:
            self._sql.commit()
            self._dirty = False

    def force_nodelete(self):
        """Force "undelete" table. Used if table was mistakenly assigned as
        deleted."""
        self._deleted = True

    def delete(
        self,
        condition: Condition = None,
        limit: int = 0,
        order: Optional[Orders] = None,
    ):
        """Delete row or rows

        Args:
            condition (Condition, optional): Condition to determine deletion
                See `Signature` class about conditional stuff. Defaults to None.
            limit (int, optional): Limit deletion by integer. Defaults to 0.
            order (Optional[Orders], optional): Order of deletion. Defaults to None.

        Returns:
            int: Rows affected
        """
        query, data = build_delete(self._table, condition, limit, order)  # type: ignore
        self._control()
        cursor = self._exec(query, data)
        rcount = cursor.rowcount
        if not self.in_transaction:
            self._sql.commit()
        else:
            self._dirty = True
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
        cursor = self._exec(query, data)
        rlastrowid = cursor.lastrowid
        if not self.in_transaction:
            self._sql.commit()
        else:
            self._dirty = True
        return rlastrowid

    def insert_multiple(self, datas: list[Data]):
        """Insert multiple values

        Args:
            datas (Iterable[Data]): Data to be inserted.
        """
        self._control()
        query, _ = build_insert(self._table, datas[0])  # type: ignore
        self._exec(query, datas, "executemany")
        if not self.in_transaction:
            self._sql.commit()
        else:
            self._dirty = True

    def insert_many(self, datas: list[Data]):
        """Alias to `insert_multiple`"""
        return self.insert_multiple(datas)

    def update(
        self,
        condition: Condition | None = None,
        data: Data | None = None,
        limit: int = 0,
        order: Optional[Orders] = None,
    ):
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
            self._table, data, condition, limit, order
        )  # type: ignore
        self._control()
        cursor = self._exec(query, data)
        rcount = cursor.rowcount
        if not self.in_transaction:
            self._sql.commit()
        else:
            self._dirty = True
        return rcount

    def update_one(
        self,
        condition: Condition | None = None,
        new_data: Data | None = None,
        order: Orders | None = None,
    ) -> int:
        """Update 1 data only"""
        return self.update(condition, new_data, 1, order)

    @overload
    def select(
        self,
        condition: Condition = None,
        only: OnlyColumn = "*",
        limit: int = 0,
        offset: int = 0,
        order: Optional[Orders] = None,
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
        order: Optional[Orders] = None,
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
        order: Optional[Orders] = None,
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
        order: Optional[Orders] = None,
        squash: Literal[False] = False,
    ) -> list[Any]:
        pass

    def select(
        self,  # pylint: disable=too-many-arguments
        condition: Condition = None,
        only: OnlyColumn | ParsedFn | JustAColumn = "*",
        limit: int = 0,
        offset: int = 0,
        order: Optional[Orders] = None,
        squash: bool = False,
    ):
        """Select data in current table. Bare .select() returns all data.

        Args:
            condition (Condition, optional): Conditions to used. Defaults to None.
            only: (OnlyColumn, ParsedFn, optional): Select what you want. Default to None.
            limit (int, optional): Limit of select. Defaults to 0.
            offset (int, optional): Offset. Defaults to 0
            order (Optional[Orders], optional): Selection order. Defaults to None.
            squash (bool): Is it squashed?

        Returns:
            Queries: Selected data
        """
        self._control()
        self._query_control()
        query, data = build_select(
            self._table, condition, only, limit, offset, order
        )  # type: ignore
        just_a_column = (isinstance(only, tuple) and len(only) == 1) or (
            isinstance(only, str) and only != "*"
        )
        with self._sql:
            cursor = self._exec(query, data)
            data = cursor.fetchall()
            if just_a_column:
                return [d[only] for d in data]
            if squash:
                return crunch(data)
            if isinstance(only, ParsedFn):
                return data[0][only.parse_sql()[0]]
            return data

    @overload
    def paginate_select(
        self,
        condition: Condition = None,
        only: OnlyColumn = "*",
        page: int = 0,
        length: int = 10,
        order: Optional[Orders] = None,
        squash: Literal[False] = False,
    ) -> Generator[Queries, None, None]:  # type: ignore
        pass

    @overload
    def paginate_select(
        self,
        condition: Condition = None,
        only: JustAColumn = "_COLUMN",
        page: int = 0,
        length: int = 10,
        order: Optional[Orders] = None,
        squash: Literal[False] = False,
    ) -> Generator[list[Any], None, None]:  # type: ignore
        pass

    @overload
    def paginate_select(
        self,
        condition: Condition = None,
        only: OnlyColumn = "*",
        page: int = 0,
        length: int = 10,
        order: Optional[Orders] = None,
        squash: Literal[True] = True,
    ) -> Generator[SquashedSqueries, None, None]:
        pass

    def paginate_select(
        self,
        condition: Condition = None,
        only: OnlyColumn | JustAColumn = "*",
        page: int = 0,
        length: int = 10,
        order: Optional[Orders] = None,
        squash: bool = False,
    ):
        """Paginate select

        Args:
            condition (Condition, optional): Confitions to use. Defaults to None.
            only (OnlyColumn, optional): Select what you want. Default to None.
            page (int): Which page number be returned first
            length (int, optional): Pagination length. Defaults to 10.
            order (Optional[Orders], optional): Order. Defaults to None.

        Yields:
            Generator[Queries, None, None]: Step-by-step paginated result.
        """

        if page < 0:
            page = 0
            order = "desc" if order in ("asc", None) else "asc"  # type: ignore
        self._control()
        self._query_control()
        start = page * length
        # ! A `only` keyword as a string or tuple of 1 element will
        # ! actually be a problem if they left alone because the end result is a list
        just_a_column = (isinstance(only, str) and only != "*") or (
            isinstance(only, tuple) and len(only) == 1
        )
        while True:
            query, data = build_select(
                self._table, condition, only, length, start, order
            )  # type: ignore
            with self._sql:
                cursor = self._exec(query, data)
                fetched = cursor.fetchmany(length)
                if len(fetched) == 0:
                    return
                if squash and not just_a_column:
                    fetched = crunch(fetched)
                if len(fetched) != length:
                    yield fetched
                    return
                yield fetched
                start += length

    @overload
    def select_one(
        self,
        condition: Condition = None,
        only: ParsedFn = _null,
        order: Optional[Orders] = None,
    ) -> Any:
        pass

    @overload
    def select_one(
        self,
        condition: Condition = None,
        only: OnlyColumn = "*",
        order: Optional[Orders] = None,
    ) -> Query:
        pass

    @overload
    def select_one(
        self,
        condition: Condition = None,
        only: JustAColumn = "_COLUMN",
        order: Optional[Orders] = None,
    ) -> Any:
        pass

    def select_one(
        self,
        condition: Condition = None,
        only: OnlyColumn | JustAColumn | ParsedFn = "*",
        order: Optional[Orders] = None,
    ):
        """Select one data

        Args:
            condition (Condition, optional): Condition to use. Defaults to None.
            only: (OnlyColumn, optional): Select what you want. Default to None.
            order (Optional[Orders], optional): Order of selection. Defaults to None.

        Returns:
            Any: Selected data
        """
        self._control()
        self._query_control()
        query, data = build_select(
            self._table, condition, only, 1, 0, order
        )  # type: ignore
        with self._sql:
            cursor = self._exec(query, data)
            data = cursor.fetchone()
            if isinstance(only, ParsedFn):
                return data[only.parse_sql()[0]]
            if not data:
                return Row()
            if isinstance(only, tuple) and len(only) == 1:
                return data[only]
            if isinstance(only, str) and only != "*":
                return data[only]
            return data

    def columns(self):
        """Table columns"""
        if self._columns is None:
            raise AttributeError("columns are undefined.")

        return tuple(self._columns)

    def add_column(self, column: Column | BuilderColumn):
        """Add column to table"""
        sql = self._sql
        column = column.to_column() if isinstance(column, BuilderColumn) else column
        if column.primary or column.unique:
            raise OperationalError(
                "New column cannot have primary or unique constraint"
            )
        if column.nullable is False and column.default is None:
            raise OperationalError(
                "New column cannot be not null while default value is \
set to null"
            )
        if column.default is not None and column.foreign:
            raise OperationalError(
                "New column must accept null default value if foreign \
constraint is enabled."
            )
        query = f"alter table {self._table} add column {extract_single_column(column)}"
        if self._columns is not None:
            self._columns.append(column)
        sql.execute(query)

    def rename_column(self, old_column: str, new_column: str):
        """Rename existing column to new column"""
        check_iter((old_column, new_column))
        query = f"alter table {self._table} rename column {old_column} to {new_column}"
        self._sql.execute(query)

    def commit(self):
        """Commit changes"""
        self._sql.commit()

    def rollback(self):
        """Rollback"""
        self._sql.rollback()
        self._dirty = False

    def count(self):
        """Count how much objects/rows stored in this table"""
        # ? Might as well uses __len__? But it's quite expensive.
        return self.select(only=count("*"))

    def __repr__(self) -> str:
        return f"<Table({self._table}) -> {self._parent_repr}>"


__all__ = ["Table"]
