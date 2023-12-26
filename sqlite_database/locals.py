"""Locals"""

from re import compile as re_compile
from re import escape as re_escape
from string import punctuation
from typing import Literal

_NO_QUOTED_STR = "\'\";"
_NO_QOUTED = re_compile(f"[{re_escape(_NO_QUOTED_STR)}]+")
_NO_UNLIKE_STR = punctuation.replace("%", "").replace("_", "")
_NO_UNLIKE = re_compile(f"[{re_escape(_NO_UNLIKE_STR)}]+")
_NPATH_STR = punctuation.replace("/", "")
_NPATH = re_compile(f"[{re_escape(_NPATH_STR)}]+")
_PATH = re_compile(f"[{re_escape('/')}]+")

PLUGINS_PATH = ('--mysql',)

_SQLITETYPES = [
    "blob", "null", "integer", "real", 'text'
]

SQLITETYPES = Literal['text'] \
    | Literal['blob'] \
    | Literal['null'] \
    | Literal['integer'] \
    | Literal['real']
SQLACTION = Literal['null'] \
    | Literal['cascade'] \
    | Literal['no act'] \
    | Literal['default'] \
    | Literal['restrict']
PRIMITIVE_TYPES = {
    "int": "integer",
    "str": "text",
    "bytes": "blob",
    "float": "real"
}
SQLITEPYTYPES = {
    "integer": "int",
    "text": "str",
    "blob": "bytes",
    "real": "float"
}

# ? I forgot what this should be...
this = object()
