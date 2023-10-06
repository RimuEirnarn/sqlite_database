"""Core database utility"""

# This module must not import anything from this package except errors.

from inspect import get_annotations
from re import Pattern
from re import compile as re_compile
from re import escape as re_escape
from sqlite3 import Cursor, connect
from string import punctuation
from typing import Any, Iterable, Type
from weakref import ref

from .errors import SecurityError, ObjectRemovedError


_INVALID_STR = punctuation.replace("_", "")
_re_valid = re_compile(f"[{re_escape(_INVALID_STR)}]+")

# I hate it when i can't import stuff


class NullObject:
    """Null object"""
    __obj = None

    def __new__(cls):
        if cls.__obj is None:
            cls.__obj = object.__new__(cls)
        return cls.__obj

    def __init__(self) -> None:
        pass

    def __repr__(self) -> str:
        return "null"

    def __str__(self) -> str:
        return repr(self)

    def __int__(self) -> int:
        return 0

    def __float__(self) -> float:
        return 0.0


class AttrDict(dict):
    """Attribute Dictionary"""

    def __getattr__(self, __name: str) -> Any:
        try:
            return super().__getattribute__(__name)
        except AttributeError:
            return self[__name]


def dict_factory(cursor, row):
    """dict factory"""
    fields = [column[0] for column in cursor.description]
    return AttrDict(zip(fields, row))
    # return {key: value for key, value in zip(fields, row)}


def sqlite_multithread_check():
    """sqlite mulththread check"""
    thread_safe = {0: 0, 2: 1, 1: 3}
    conn = connect(":memory:", check_same_thread=False)
    data = conn.execute("select * from pragma_compile_options where compile_options \
like 'THREADSAFE=%'")\
        .fetchone()[0]
    conn.close()

    threadsafety_value = int(data.split("=")[1])
    return thread_safe[threadsafety_value]


def matches(pattern: Pattern, value: str):
    """matches"""
    if len(pattern.findall(value)) == 0:
        return False
    return True


def check_one(data: str):
    """check one to check if a string contains illegal character"""
    if matches(_re_valid, data) is True:
        raise SecurityError("Cannot parse unsafe data.")
    return data


def check_iter(data: Iterable[str]):
    """An iterable checks as it's check_one"""
    for val in data:
        yield check_one(val)


class WithCursor(Cursor):
    """With cursor"""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type and exc_value and traceback:
            return True
        self.connection.commit()
        return True

    def __repr__(self) -> str:
        return type(self).__name__


class Ref:
    """Weakref object Referece (descriptor)"""
    _null = object()
    def __init__(self):
        self._ref = self._null

    def __get__(self, obj, objtype=None):
        if self._ref is self._null:
            raise ValueError("Reference is null, no object is specified")
        if (object_ := self._ref()): # type: ignore
            return object_
        raise ObjectRemovedError("object is removed")

    def __set__(self, obj, value):
        self._ref = ref(value)

def future_class_var_isdefined(type_: Type[Any], future_attr: str):
    """Is a future class var defined?"""
    annotations = get_annotations(type_)
    if future_attr in annotations:
        try:
            getattr(type_, future_attr)
        except AttributeError:
            return True
    return False

def test_installed():
    """Test if project is truly installed. It was meant for docs compatibility and thus,
    always returns true"""
    return True

null = NullObject()


def get_type_from_mapping(type: str, mapping: dict[str, str]) -> str:
    """get type from mapping"""
    if not type in mapping:
        raise ValueError(f"{type} was not defined in the mapping.")
    return mapping[type]

__all__ = ['null', 'future_class_var_isdefined', 'WithCursor', 'check_iter', 'check_one',
           'matches', 'AttrDict', 'NullObject', 'sqlite_multithread_check',
           'get_type_from_mapping']
