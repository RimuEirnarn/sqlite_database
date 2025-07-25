"""Worker Connection"""
# pylint: disable=ungrouped-imports,possibly-used-before-assignment,too-few-public-methods

# import os
from sys import version_info
from concurrent.futures import Future
from queue import Empty, Queue
from sqlite3 import Connection
from multiprocessing import Event as EventProcess, Process, freeze_support
from threading import Thread, Event as EventThread
from typing import Any, Literal, TypeAlias
from atexit import register as finalize

from ..errors import VersionError

WorkerType: TypeAlias = Literal["thread"] | Literal["process"]
FEATURE_MIN_VERSION = (3, 13)

if version_info > FEATURE_MIN_VERSION:
    from queue import ShutDown

class Worker:
    """Worker"""

    def __init__(self, *args, worker_type: WorkerType = "thread", **kwargs):
        # print(args, worker_type, kwargs)
        if version_info < FEATURE_MIN_VERSION:
            version = f"{version_info.major}.{version_info.minor}"
            minimal = f"{FEATURE_MIN_VERSION[0]}.{FEATURE_MIN_VERSION[1]}"
            raise VersionError(
                f"Python {version} (current version) cannot use Worker feature, min {minimal}"
            )
        self.conn = Connection(*args, **kwargs)
        self.queue = Queue()
        self.name = f"WorkerDB[{worker_type}]"
        self.daemon = True
        if worker_type == "thread":
            self.event = EventThread()
            self.worker = Thread(target=self._run, name=self.name, daemon=self.daemon)
        elif worker_type == "process":
            freeze_support()
            self.event = EventProcess()
            self.worker = Process(target=self._run, name=self.name, daemon=self.daemon)
        self.event.set()
        self.worker.start()
        finalize(self.close)

    def _run(self):
        while self.event.is_set():
            try:
                # print(f"[{self.name}] Fetching...")
                fn, args, kwargs, fut = self.queue.get(timeout=0.01)
            except Empty:
                # print(f"[{self.name}] Empty!")
                continue
            except ShutDown:
                break
            if fn is None:
                # print(f"[{self.name}] Receives stop signal, closing self...")
                fut.set_result(None)
                self.queue.task_done()
                self.queue.shutdown(True)
                break
            try:
                if callable(fn):
                    # print(f'[{self.name}] what={fn!r} args={args} kwargs={kwargs}')
                    res = fn(*args, **kwargs)
                    fut.set_result(res)
                else:
                    # print(f'[{self.name}] what={fn!r} value={kwargs["value"]}')
                    setattr(self.conn, fn, kwargs["value"])
                    fut.set_result(None)
            except Exception as e:  # pylint: disable=broad-exception-caught
                fut.set_exception(e)
            finally:
                self.queue.task_done()
            # print(f"[{self.name}] Stalling...")
        # print(f"[{self.name}] Quit")

    def push(self, fn, *args, **kwargs):
        """Push to worker"""
        fut = Future()
        try:
            self.queue.put((fn, args, kwargs, fut))
        except ShutDown:
            fut.set_result(None)
            return fut.result()
        return fut.result()  # blocks until worker finishes

    def close(self, push=True):
        """Close this worker"""
        # print(f"[{self.name}] close() is called, shutting down")
        self.event.clear()
        if push:
            self.push(None)
        self.worker.join(0)
        self.conn.close()


class WorkerCursor:
    """Worker cursor"""

    __slots__ = ("_worker", "_cursor")

    def __init__(self, worker, real_cursor):
        self._worker = worker
        self._cursor = real_cursor

    def __getattr__(self, item):
        # print(self, item)
        if item in self.__slots__:
            return super().__getattribute__(item)
        attr = getattr(self._cursor, item)
        if callable(attr):
            return lambda *a, **kw: self._worker.push(attr, *a, **kw)
        return attr


class WorkerConnection:
    """Worker connection"""

    def __init__(self, *args, worker_type: WorkerType = "thread", **kwargs):
        self._real = Worker(*args, worker_type=worker_type, **kwargs)

    def __getattr__(self, item):
        # print(self, item)
        if item in ("_real", "cursor"):
            return super().__getattribute__(item)
        conn = self._real.conn
        attr = getattr(conn, item)
        if callable(attr):
            return lambda *a, **kw: self._real.push(attr, *a, **kw)
        return attr

    def cursor(self, *args, **kwargs):
        """Return cursor object"""
        real = self._real.push(getattr(self._real.conn, "cursor"), *args, **kwargs)
        return WorkerCursor(self._real, real)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_real":
            super().__setattr__(name, value)
            return
        self._real.push(name, value=value)

    def __enter__(self):
        return self.cursor()

    def __exit__(self, _, exc, __):
        pass
