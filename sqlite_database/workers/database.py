"""Database Worker"""

from sqlite_database._utils import dict_factory, NoopResource
from sqlite_database.database import Database
from sqlite_database.workers.connection import WorkerConnection, WorkerType
from sqlite_database.errors import VersionError


class DatabaseWorker(Database):
    """Database Worker"""

    def __init__(self, path: str, worker_type: WorkerType = "thread", **kwargs) -> None:
        self._worker_type: WorkerType = worker_type
        super().__init__(path, **kwargs)

    def _create_connection(self):
        timeout = self._kwargs.pop("timeout", 30)
        if not isinstance(timeout, int):
            timeout = 30
        # conn = connect(
            # self._path,
            # timeout=timeout,
            # isolation_level=self._kwargs.pop("isolation_level", None),
            # check_same_thread=self._kwargs.pop("check_same_thread", False)
        # )
        # conn.row_factory = dict_factory
        try:
            self._database = WorkerConnection(
                self._path,
                worker_type=self._worker_type,
                timeout=timeout,
                isolation_level=self._kwargs.pop("isolation_level", None),
                check_same_thread=self._kwargs.pop("check_same_thread", False)
            )
            self._database.row_factory = dict_factory
            self._database.execute("PRAGMA journal_mode=WAL;")
            self._database.execute(f'PRAGMA busy_timeout={timeout * 1000};')
        except VersionError:
            self._database = NoopResource()
            raise

    def close(self):
        self._database.close()
        self._database.join() # type: ignore

    def join(self):
        """Join the worker thread/process"""
        self._database.join() # type: ignore
