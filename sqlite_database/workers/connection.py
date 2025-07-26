"""Worker Connection"""

# pylint: disable=ungrouped-imports,possibly-used-before-assignment,too-few-public-methods,no-name-in-module,no-member

# import os
from sys import version_info
from concurrent.futures import Future
from queue import Empty, Queue
from sqlite3 import Connection, Cursor
from multiprocessing import Event as EventProcess, Process, freeze_support
from threading import Thread, Event as EventThread
from typing import Any, Literal, TypeAlias
from atexit import register as finalize

from ..errors import Rejection

WorkerType: TypeAlias = Literal["thread"] | Literal["process"]
FEATURE_MIN_VERSION = (3, 13)

if version_info > FEATURE_MIN_VERSION:
    from queue import ShutDown  # type: ignore
else:

    class ShutDown(RuntimeError):
        """Raised when put/get with shut-down queue."""


def is_shutdown(worker: "Worker"):
    """Is shutdown?"""
    if worker.is_closed:
        return lambda *a, **kw: None
    return lambda *a, **kw: worker.push(worker.conn.close, "connection", *a, **kw)


class Worker:
    """Worker"""

    def __init__(self, *args, worker_type: WorkerType = "thread", **kwargs):
        self.conn = Connection(*args, **kwargs)
        self.queue = Queue()
        self.name = f"WorkerDB[{worker_type}]"
        self.daemon = False
        if worker_type == "thread":
            self.event = EventThread()
            self.worker = Thread(target=self._run, name=self.name, daemon=self.daemon)
        elif worker_type == "process":
            freeze_support()
            self.event = EventProcess()
            self.worker = Process(target=self._run, name=self.name, daemon=self.daemon)
        self.accepting = self.event
        self._closing = False
        self.event.set()
        self.worker.start()
        finalize(self.close)

    def recall(self):
        """Recall remainding queues"""
        while True:
            try:
                fn, _, args, kwargs, fut = self.queue.get_nowait()
            except Empty:
                break
            try:
                if callable(fn):
                    res = fn(*args, **kwargs)
                    fut.set_result(res)
                else:
                    fut.set_result(None)
            except Exception as e:  # pylint: disable=broad-exception-caught
                fut.set_exception(e)
            finally:
                self.queue.task_done()

    def _run(self):
        while True:
            try:
                fn, owner, args, kwargs, fut = self.queue.get(timeout=0.01)
            except Empty:
                if self._closing:
                    break
                continue
            except ShutDown:
                break

            # If close signal is received, finish all tasks and quit
            if fn is None or (
                getattr(fn, "__name__", "") == "close" and owner == "connection"
            ):
                fut.set_result(None)
                self.queue.task_done()
                self._closing = True
                self.event.clear()
                self.recall()  # Finish all remaining tasks
                break

            try:
                if callable(fn):
                    res = fn(*args, **kwargs)
                    fut.set_result(res)
                else:
                    setattr(self.conn, fn, kwargs["value"])
                    fut.set_result(None)
            except Exception as e:  # pylint: disable=broad-exception-caught
                fut.set_exception(e)
            finally:
                self.queue.task_done()
        # Ensure connection is closed
        self.conn.close()

    def push(self, fn, owner: str, *args, **kwargs):
        """Push to worker"""
        if not self.accepting.is_set() or self._closing:
            exc = Rejection("Cannot push during shutdown")
            exc.add_note(f"Caller: {fn}")
            raise exc
        fut = Future()
        try:
            self.queue.put((fn, owner, args, kwargs, fut))
        except ShutDown:
            fut.set_result(None)
            return fut.result()
        return fut.result()  # blocks until worker finishes

    @property
    def is_closed(self):
        """Return true if worker is closed"""
        return self._closing

    def close(self, push=True):
        """Close this worker"""
        if self._closing:
            return
        self._closing = True
        self.event.clear()
        if push:
            # Push a close signal to the queue
            fut = Future()
            self.queue.put((lambda: None, "connection", (), {}, fut))
            fut.result()
        self.worker.join()

    def join(self, timeout: float = 0):
        """Join this worker"""
        self.worker.join(timeout)


class WorkerCursor:
    """Worker cursor"""

    __slots__ = ("_worker", "_cursor")

    def __init__(self, worker: Worker, real_cursor: Cursor):
        self._worker: Worker = worker
        self._cursor: Cursor = real_cursor

    def __getattr__(self, item):
        # print(self, item)
        if item in self.__slots__:
            return super().__getattribute__(item)

        attr = getattr(self._cursor, item)
        if callable(attr):
            return lambda *a, **kw: self._worker.push(attr, "cursor", *a, **kw)
        return attr


class WorkerConnection:
    """Worker connection"""

    def __init__(self, *args, worker_type: WorkerType = "thread", **kwargs):
        self._real: Worker = Worker(*args, worker_type=worker_type, **kwargs)

    def __getattr__(self, item):
        # print(self, item)
        if item in ("_real", "cursor"):
            return super().__getattribute__(item)

        if item in ("join",):
            return getattr(self._real, item)

        conn = self._real.conn
        attr = getattr(conn, item)
        if item == "close":
            return is_shutdown(self._real)

        if callable(attr):
            return lambda *a, **kw: self._real.push(attr, "connection", *a, **kw)
        return attr

    def cursor(self, *args, **kwargs):
        """Return cursor object"""
        real = self._real.push(
            getattr(self._real.conn, "cursor"), "connection", *args, **kwargs
        )
        return WorkerCursor(self._real, real)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_real":
            super().__setattr__(name, value)
            return
        self._real.push(name, "connection", value=value)

    def __enter__(self):
        return self.cursor()

    def __exit__(self, _, exc, __):
        pass
