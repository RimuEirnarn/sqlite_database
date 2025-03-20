"""Typing Extensions"""

# pylint: disable=unnecessary-ellipsis
from typing import Any, Literal, TypedDict, TypeAlias, TypeVar

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
tuple_list: TypeAlias = list[T] | tuple[T, ...] # pylint: disable=invalid-name
null = object()


class _MasterQuery(TypedDict):
    """Master Query"""

    type: str
    name: str
    tbl_name: str
    rootpage: int
    sql: str
