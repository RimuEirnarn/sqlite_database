"""Typing Extensions"""

# pylint: disable=unnecessary-ellipsis
from typing import Any, Literal, TypedDict, TypeAlias, TypeVar


T = TypeVar("T")
Order: TypeAlias = tuple[str, Literal['asc'] | Literal['desc']]
Orders: TypeAlias = tuple[Order, ...] | Order
Data: TypeAlias = dict[str, Any]
Query: TypeAlias = dict[str, Any]  # type: ignore
OnlyColumn: TypeAlias = tuple[str, ...] | Literal["*"]
JustAColumn: TypeAlias = str | tuple[str] # pylint: disable=invalid-name
Queries: TypeAlias = list[Query] | dict[str, list[Any]]  # type: ignore
SquashedSqueries: TypeAlias = dict[str, list[Any]]  # type: ignore
tuple_list: TypeAlias = list[T] | tuple[T, ...] # pylint: disable=invalid-name
null = object()


class MasterQuery(TypedDict):
    """Master Query"""

    type: str
    name: str
    tbl_name: str
    rootpage: int
    sql: str
