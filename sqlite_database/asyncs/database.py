"""AsyncDatabase"""

from sqlite3 import connect, Connection
from threading import local

from .table import AsyncTable
from ..database import Database
from .._utils import dict_factory


class AsyncDatabase(Database):
    """Async (threads, subprocess) ready"""

    def __init__(self, path: str, **kwargs) -> None:
        self._local = local()
        super().__init__(path, **kwargs)
        self._table_class = AsyncTable

    def _create_connection(self):
        conn = getattr(self._local, "conn", None)
        if conn is None:
            timeout = self._kwargs.pop('timeout', 30)
            conn = connect(
                self._path,
                timeout=timeout,
                isolation_level=self._kwargs.pop("isolation_level", None),
                check_same_thread=self._kwargs.pop("check_same_thread", False)
            )
            conn.row_factory = dict_factory
            conn.execute("PRAGMA journal_mode=WAL;")
            if isinstance(timeout, int):
                conn.execute(f'PRAGMA busy_timeout={timeout * 1000};')
            self._local.conn = conn

    @property
    def _database(self) -> Connection:
        return self._local.conn
