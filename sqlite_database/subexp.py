"""Sub expression"""
# pylint: disable=unused-import


from .typings import NamedTuple, Literal
from .functions import ParsedFn


class SelectExpr(NamedTuple):
    """Select (low level) expression"""
    what: "str | ParsedFn | SelectExpr | tuple[str, ...]"
    from_: str | None = None
    where: tuple[tuple[str, str] | tuple[str, ParsedFn], ...] | None = None
    limit: int = 0
    offset: int = 0
    order: "Literal['asc', 'desc'] | SelectExpr | None" = None

select = SelectExpr
