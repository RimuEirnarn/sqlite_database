"""Typing Extensions"""
# pylint: disable=unnecessary-ellipsis
from sys import maxsize as sys_maxsize
from typing import Any, Literal, Protocol, SupportsIndex, TypedDict

from ._utils import AttrDict

Orders = dict[str, Literal['asc'] | Literal['desc']]
Data = dict[str, Any]
Query = AttrDict[str, Any]  # type: ignore
OnlyColumn = tuple[str, ...] | None
Queries = list[Query] | AttrDict[str, list[Any]] # type: ignore
null = object()


class _MasterQuery(TypedDict):
    """Master Query"""
    type: str
    name: str
    tbl_name: str
    rootpage: int
    sql: str


class TypicalNamedTuple(Protocol):
    """Typical Named Tuple"""

    def __getitem__(self, __key: int) -> Any:
        ...

    def count(self, __value: Any) -> int:
        """count"""
        ...

    def index(self,
              __value: Any,
              __start: SupportsIndex = 0,
              __end: SupportsIndex = sys_maxsize) -> int:
        """index"""
        ...

    def _asdict(self) -> dict[str, Any]:
        ...
