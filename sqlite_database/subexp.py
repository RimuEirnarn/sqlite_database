"""Sub expression"""

# pylint: disable=unused-import


from typing import NamedTuple, Literal
from .functions import ParsedFn


class SelectExpr(NamedTuple):  # pylint: disable=too-few-public-methods
    """Select (low level) expression"""

    what: "str | ParsedFn | SelectExpr | tuple[str, ...]"
    from_: str | None = None
    where: tuple[tuple[str, str] | tuple[str, ParsedFn], ...] | None = None
    limit: int = 0
    offset: int = 0
    order: "Literal['asc', 'desc'] | SelectExpr | None" = None


select = SelectExpr
