"""Async Table"""

# pylint: disable=invalid-overridden-method
import asyncio
from contextvars import ContextVar

from ..table import Table
from ..query_builder import Condition
from ..typings import Orders

# Context-local transaction depth stack per async task
_tx_stack = ContextVar("_tx_stack", default=[])


class AsyncTable(Table):
    """Async (threading/multiprocess ready) Table"""

    def __init__(self, parent, table: str, columns=None, aggressive_select=False):
        super().__init__(parent, table, columns, False)
        if (self._columns is None and aggressive_select) and table != "sqlite_master":
            asyncio.get_event_loop().run_until_complete(
                asyncio.to_thread(self._fetch_columns)
            )

    async def _begin_transaction(self):
        """Start a transaction or savepoint depending on depth."""
        stack = list(_tx_stack.get())  # copy since ContextVar values are immutable
        depth = len(stack)

        if depth == 0:
            await asyncio.to_thread(self._sql.execute, "BEGIN TRANSACTION")
        else:
            savepoint_name = f"sp_{depth}"
            await asyncio.to_thread(self._sql.execute, f"SAVEPOINT {savepoint_name}")

        stack.append(True)
        _tx_stack.set(stack)

    async def _commit_transaction(self):
        """Commit or release savepoint depending on depth."""
        stack = list(_tx_stack.get())
        depth = len(stack)

        if depth == 1:
            await asyncio.to_thread(self._sql.commit)
        elif depth > 1:
            savepoint_name = f"sp_{depth-1}"
            await asyncio.to_thread(
                self._sql.execute, f"RELEASE SAVEPOINT {savepoint_name}"
            )

        stack.pop()
        _tx_stack.set(stack)

    async def _rollback_transaction(self):
        """Rollback or rollback to savepoint depending on depth."""
        stack = list(_tx_stack.get())
        depth = len(stack)

        if depth == 1:
            await asyncio.to_thread(self._sql.rollback)
        elif depth > 1:
            savepoint_name = f"sp_{depth-1}"
            await asyncio.to_thread(
                self._sql.execute, f"ROLLBACK TO SAVEPOINT {savepoint_name}"
            )

        stack.pop()
        _tx_stack.set(stack)

    # ✅ async context manager compatible with your original Table
    async def __aenter__(self):
        await self._begin_transaction()
        return self

    async def __aexit__(self, exc_type, *_):
        if exc_type:
            await self._rollback_transaction()
        else:
            await self._commit_transaction()

    async def begin(self):
        """Begin"""
        await self._begin_transaction()

    async def commit(self):
        await self._commit_transaction()

    async def rollback(self):
        await self._rollback_transaction()

    async def delete(
        self, where: Condition = None, limit: int = 0, order: Orders | None = None
    ):
        await asyncio.to_thread(self.delete, where, limit, order)
