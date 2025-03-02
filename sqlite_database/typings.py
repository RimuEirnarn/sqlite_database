"""Typing Extensions"""

# pylint: disable=unnecessary-ellipsis
from sys import maxsize as sys_maxsize
from typing import Any, Literal, Protocol, SupportsIndex, TypedDict, TypeAlias, TypeVar

from sqlite_database.functions import ParsedFn  # pylint: disable=unused-import

from ._utils import Row

T = TypeVar("T")
Order: TypeAlias = tuple[str, Literal['asc'] | Literal['desc']]
Orders: TypeAlias = tuple[Order, ...] | Order
Data: TypeAlias = dict[str, Any]
Query: TypeAlias = Row[str, Any]  # type: ignore
OnlyColumn: TypeAlias = tuple[str, ...] | Literal["*"]
JustAColumn: TypeAlias = str | tuple[str] # pylint: disable=invalid-name
Queries: TypeAlias = list[Query] | Row[str, list[Any]]  # type: ignore
SquashedSqueries: TypeAlias = Row[str, list[Any]]  # type: ignore
tuple_list: TypeAlias = list[T] | tuple[T, ...]
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
