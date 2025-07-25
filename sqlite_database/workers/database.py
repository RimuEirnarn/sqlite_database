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
        try:
            self._database = WorkerConnection(
                self._path, worker_type=self._worker_type, **self._kwargs
            )
            self._database.row_factory = dict_factory
        except VersionError:
            self._database = NoopResource()
            raise
