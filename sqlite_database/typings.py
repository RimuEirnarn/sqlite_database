"""Typing Extensions"""

# pylint: disable=unnecessary-ellipsis
from sys import maxsize as sys_maxsize
from typing import Any, Literal, Protocol, SupportsIndex, TypedDict

from sqlite_database.functions import ParsedFn  # pylint: disable=unused-import

from ._utils import Row

Orders = dict[str, Literal["asc"] | Literal["desc"]]
Data = dict[str, Any]
Query = Row[str, Any]  # type: ignore
OnlyColumn = tuple[str, ...] | Literal["*"]
Queries = list[Query] | Row[str, list[Any]]  # type: ignore
Queries = list[Query]
SquashedSqueries = Row[str, list[Any]]  # type: ignore
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

    def __getitem__(self, __key: int) -> Any: ...

    def count(self, __value: Any) -> int:
        """count"""
        ...

    def index(
        self,
        __value: Any,
        __start: SupportsIndex = 0,
        __end: SupportsIndex = sys_maxsize,
    ) -> int:
        """index"""
        ...

    def _asdict(self) -> dict[str, Any]: ...
