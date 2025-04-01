"""Query Builder"""

from dataclasses import dataclass
from functools import lru_cache
from shlex import shlex
from typing import Any, Iterable, Literal, Optional, TypeAlias
from uuid import uuid4

from .subquery import SubQuery
from .functions import ParsedFn, _function_extract
from .errors import SecurityError
from ._utils import check_one, null, check_iter, Null
from .column import Column
from .locals import _SQLITETYPES, SQLACTION
from .signature import Signature
from .typings import _MasterQuery, Data, Orders

ConditionDict: TypeAlias = dict[str, Signature | ParsedFn | SubQuery | Any]
ConditionList: TypeAlias = list[tuple[str, Signature | SubQuery | ParsedFn]]
Condition: TypeAlias = ConditionDict | ConditionList | None
CacheCond: TypeAlias = tuple[tuple[str, Signature | SubQuery | ParsedFn], ...] | None
CacheOrders: TypeAlias = tuple[str, Literal["asc", "desc"]] | ParsedFn | None
CacheData: TypeAlias = tuple[str, ...]
OnlyColumn = tuple[str, ...] | str | ParsedFn
DEFAULT_MAPPINGS = {value: value for value in _SQLITETYPES}
SQL_ACTIONS = {"null": "set null"}
MAX_SUBQUERY_STACK_LIMIT = 10

def set_subquery_stack_limit(value: int):
    """Set subquery stack limit"""
    global MAX_SUBQUERY_STACK_LIMIT # pylint: disable=global-statement
    if MAX_SUBQUERY_STACK_LIMIT <= 0:
        raise ValueError("Cannot set limit below 1")
    MAX_SUBQUERY_STACK_LIMIT = value

def generate_ids():
    """Generate ids for statements"""
    return str(uuid4().int)


class TableCreationExtractor:
    """Base processor for table creation"""

    def __init__(self, columns: Iterable[Column], type_mappings: dict[str, str] | None):
        self.columns = columns
        self.type_mappings = _get_type_mappings(type_mappings)
        self.primaries: list[Column] = []
        self.foreigns: list[Column] = []
        self.string = ""

    def process_columns(self):
        """Process each columns"""
        self.string = _iterate_etbc_step1(
            self.columns, self.string, self.primaries, self.foreigns, self.type_mappings
        )

    def add_primary_keys(self):
        """Add primary key constraints"""
        if self.primaries:
            self.string += (
                f" primary key ({', '.join((col.name for col in self.primaries))}),"
            )

    def add_foreign_keys(self):
        """Add foreign key constraints"""
        for column in self.foreigns:
            stable, sname = column.source, column.source_column
            self.string += (
                f" foreign key ({column.name}) references {stable} ({sname})"
                f" on delete {_iterate_sql_action(column.on_delete)}"  # type: ignore
                f" on update {_iterate_sql_action(column.on_update)},"  # type: ignore
            )

    def extract(self) -> str:
        """Extract everything into a string"""
        self.process_columns()
        self.add_primary_keys()
        self.add_foreign_keys()
        return self.string[1:-1]


@dataclass(frozen=True)
class QueryParams:
    """Encapsulates parameters for building SQL queries."""

    table_name: str
    condition: Optional[CacheCond] = None
    only: Optional[OnlyColumn] = None
    limit: int = 0
    offset: int = 0
    order: Optional[CacheOrders] = None
    data: Optional[CacheData] = None

    def __hash__(self):
        """Custom hash function to ensure compatibility with lru_cache."""
        return hash(
            (
                self.table_name,
                self.condition,
                self.only,
                self.limit,
                self.offset,
                self.order,
                self.data,
            )
        )


def extract_table(  # pylint: disable=too-many-locals
    table_creation: str,
) -> list[Column]:
    """Extract SQLite table string"""
    data = table_creation[table_creation.find("(") + 1 : -1]
    cols, upheld = basic_extract(table_creation)
    shlexed = list(shlex(data))
    _, paren_wrap, filtered = filter_extraction(data, shlexed)

    # for efficiency, is this part efficient though?
    # although, can SOMEONE have a million columns on a sqlite table?
    # So, the efficiency on this blob isn't a concern.
    for column_string in filtered.split(","):
        column_shlexed = list(shlex(column_string))
        for tindex, token in enumerate(column_shlexed):
            if token.lower() == "primary":
                next_ = tindex + 2
                str_wrap = "".join(column_shlexed[next_ : next_ + 2])
                if str_wrap.startswith(":wrap"):
                    wrap = paren_wrap[str_wrap]
                else:
                    wrap = str_wrap
                for name in (
                    wrap[1:-1].split(",") if wrap.startswith("(") else wrap.split(",")
                ):
                    upheld[name][4] = True
                continue
            if token.lower() == "foreign":
                next_ = tindex + 2
                str_wrap = "".join(column_shlexed[next_ : next_ + 2])
                if str_wrap.startswith(":wrap"):
                    wrap = paren_wrap[str_wrap]
                else:
                    wrap = str_wrap
                name = (
                    wrap[1:-1] if wrap.startswith("'") or wrap.startswith('"') else wrap
                )
                name = wrap[1:-1] if wrap.startswith("(") else wrap
                tb_index = next_ + 3
                tb_col = tb_index + 1
                source_col_str = paren_wrap[f":{column_shlexed[tb_col+1]}"][1:-1]
                sources = f"{column_shlexed[tb_index]}/{source_col_str}"
                upheld[name][3] = sources
                upheld[name][2] = True
                if "delete" in column_shlexed:
                    delete_index = column_shlexed.index("delete")
                    upheld[name].append(column_shlexed[delete_index + 1])
                if "update" in column_shlexed:
                    uindex = column_shlexed.index("update")
                    upheld[name].append(column_shlexed[uindex + 1])

    for _, upheld_column in upheld.items():
        cols.append(Column(*upheld_column))
    return cols


def fetch_columns(_master_query: _MasterQuery):
    """Fetch columns of a table. `_master_query` is originated from select()
    on sqlite_master table"""
    sql = _master_query["sql"]
    return extract_table(sql)


def extract_signature( # pylint: disable=too-many-locals,too-many-branches
    filter_: Condition | CacheCond = None, suffix: str = "_check", depth: int = 0  # type: ignore
):
    """Extract filter signature."""
    if depth < 0 or depth >= MAX_SUBQUERY_STACK_LIMIT:
        raise RecursionError("Subquery builder has reached recursion limit of"
                             f"{MAX_SUBQUERY_STACK_LIMIT}")
    if filter_ is None:
        return "", {}
    if isinstance(filter_, (list, tuple)):
        filter_: ConditionDict = dict(filter_)
    call_id = generate_ids()
    string = "where"
    data: dict[str, Any] = {}
    last = 1
    for key, value in filter_.items():
        condition_id = generate_ids()
        if not isinstance(value, Signature):
            value = Signature(value, "=")
        old_data = value.value
        val = (
            Signature(
                f":{key}_{call_id}_{depth}_{condition_id}_{suffix}",
                value.generate(),
                value.data,
            )
            if value.value is not null
            else value
        )
        if isinstance(value.value, SubQuery):
            subq, subq_data = extract_subquery(value.value, depth=depth + 1)
            string += f" {key} in ({subq}) and"
            last = 4
            data.update(subq_data)
            continue

        middle = val.generate()
        if val.normal_operator:
            string += f" {key}{middle}{val.value} and"
            last = 4
        if val.is_in:
            vals = tuple(
                (
                    f":prop_{condition_id}_val_in{index}"
                    for index, _ in enumerate(val.data)  # type: ignore
                )
            )
            string += f" {key} {middle} ({', '.join(vals)}) and"
            last = 4
            for key0, val0 in zip(vals, val.data):  # type: ignore
                data[key0[1:]] = val0
            continue
        if val.is_between:
            vdata: tuple[int, int] = val.data  # type: ignore
            if not all(map(lambda x: isinstance(x, (int, float)), vdata)):
                raise SecurityError("Values for between constraint is not int/float")
            string += f" {key} {middle} {vdata[0]!r} and {vdata[1]!r} and"
            last = 4
        if val.is_like:
            vdata: str = val.data  # type: ignore
            string += f" {key} {middle} {vdata!r} and"
            last = 4
        if val.value is not null:
            data[f"{key}_{call_id}_{depth}_{condition_id}_{suffix}"] = old_data

    return string[:-last], data


def basic_extract(table_creation: str):  # pylint: disable=too-many-locals
    """basic extraction for table"""
    data = table_creation[table_creation.find("(") + 1 : -1]
    cols = []
    upheld: dict[str, list[Any]] = {}
    for constr in data.split(","):
        name, type_, defaults, sources = "", "", None, ()
        primary = foreign = notnull = unique = False
        base_columns = list(shlex(constr))
        if base_columns[1] not in _SQLITETYPES:
            break  # Other constraint
        (
            name,
            type_,
        ) = (
            base_columns[0],
            base_columns[1],
        )
        if len(base_columns) == 2:
            # cols.append(Column(name, type_))  # type: ignore
            upheld[name] = [name, type_, False, None, False, False, True, None]
            continue
        for token in base_columns:
            token_lowered = token.lower()
            if token_lowered == "defaults":
                defaults = base_columns[base_columns.index(token) + 1]
                defaults = (
                    defaults
                    if defaults[0] != '"' or defaults[0] != "'"
                    else defaults[1:-1]
                )
            if token_lowered == "primary":
                primary = True
            if token_lowered == "foreign":
                foreign = True
            if token_lowered == "reference":
                tb_index = base_columns.index(token) + 1
                tb_col = tb_index + 1
                sources = (base_columns[tb_index], base_columns[tb_col][1:-1])
            if token_lowered == "null":
                notnull = base_columns[base_columns.index(token) - 1].lower() == "not"
            if token_lowered == "unique":
                unique = True
        upheld[name] = [
            name,
            type_,
            foreign,
            f"{sources[0]}/{sources[1]}" if sources else None,
            primary,
            unique,
            not notnull,
            defaults if defaults else None,
        ]
    return cols, upheld


# Old place of function_extract
function_extract = _function_extract


def filter_extraction(string: str, shlexed: list[str]):
    """
    A function step of table extraction. Used to replace quoted and parens with parameter.

    Args:
        string (str): The input string containing the table creation SQL.
        shlexed (list[str]): The tokenized list of the input string.

    Returns:
        tuple[dict[str, str], dict[str, str], str]: A tuple containing:
            - A dictionary mapping placeholders to quoted strings.
            - A dictionary mapping placeholders to parenthesized strings.
            - The modified string with placeholders.
    """

    quoted_wrap = {}
    paren_wrap = {}
    new_string = string
    for index, shlex_string in enumerate(shlexed):
        # ? this attempt to replace all quoted string to a format-able stuff.
        if shlex_string.startswith("'") or shlex_string.startswith('"'):
            quoted_wrap[f":index{index}"] = shlex_string
            new_string = new_string.replace(shlex_string, f":index{index}")

    while (index := new_string.find("(")) != -1:
        # ? this attempt to replace all brackets with format-able stuff
        last = new_string.find(")") + 1
        selected = new_string[index:last]
        new_string = new_string.replace(selected, f":wrap{len(paren_wrap)}")
        paren_wrap[f":wrap{len(paren_wrap)}"] = selected
    return quoted_wrap, paren_wrap, new_string


def build_update_data(data: dict[str, Any] | CacheData, suffix: str = "_set"):
    """Build update data, used to parameterized update data.
    Suffix is used to make sure there's no collisions with others. Use this with caution.
    """
    string = ""
    that: dict[str, str] = {}
    for key in data:
        check_one(key)
        string += f"{key}=:{key}{suffix}, "
        that[f"{key}{suffix}"] = f":{key}{suffix}"
    return string[:-2], that


def format_paramable(data: dict[str, Any] | tuple[str, ...]):
    """Format a data to parameterized data."""
    that: dict[str, str] = {}
    if isinstance(data, dict):
        for key in data:
            check_one(key)
            that[key] = f":{key}"
    else:
        for key in data:
            check_one(key)
            that[key] = f":{key}"
    return that


def combine_keyvals(keydict: dict[str, Any], valuedict: dict[str, Any] | CacheData):
    """Combine key dictionary with value dictionary. The first dictionary will only
    ignore the values while value dict ignore the keys.
    Mapping[key, _] -> keydict
    Mapping[_, value] -> valuedict"""
    if len(keydict) != len(valuedict):
        raise IndexError("One dictionary is larger. It must be equal.")
    new: dict[str, Any] = {}
    if isinstance(valuedict, dict):
        for key0, key1 in zip(keydict, valuedict):
            new[key0] = valuedict[key1]
    else:
        for key0, val1 in zip(keydict, valuedict):
            new[key0] = val1
    return new


def extract_single_column(column: Column):
    """Extract a column class to sqlite column creation query"""
    foreign = column.foreign
    primary = column.primary
    string = f"{column.name} {column.type}"
    if not column.nullable:
        string += " not null"
    if column.unique:
        string += " unique"
    if column.default:
        string += f" default {repr(column.default)}"

    if primary:
        string += "primary key"
    if foreign:
        string += f"foreign key references {column.source} ({column.source_column})"
    return string


def _process_column_constraints(column: Column, ctype: str) -> str:
    """Process constraints for a single column."""
    constraints = f" {column.name} {ctype}"
    if not column.nullable:
        constraints += " not null"
    if column.unique:
        constraints += " unique"
    if column.default:
        constraints += f" default {repr(column.default)}"
    return constraints


def _iterate_etbc_step1(
    columns: Iterable[Column],
    string: str,
    primaries: list[Column],
    foreigns: list[Column],
    maps: dict[str, str],
):
    for column in columns:
        ctype = maps.get(column.type, column.type)
        string += _process_column_constraints(column, ctype)
        if column.raw_source:
            foreigns.append(column)
        if column.primary:
            primaries.append(column)
        string += ","
    return string


def _iterate_sql_action(action: SQLACTION):
    return SQL_ACTIONS.get(action, action)


def _get_type_mappings(type_mappings: dict[str, str] | None) -> dict[str, str]:
    """Get the merged type mappings."""
    maps = DEFAULT_MAPPINGS.copy()
    if type_mappings:
        maps.update(type_mappings)
    return maps


def extract_table_creations(
    columns: Iterable[Column], type_mappings: dict[str, str] | None = None
):
    """Extract columns classes to sqlite table creation query."""
    extractor = TableCreationExtractor(columns, type_mappings)
    return extractor.extract()


@lru_cache
def extract_subquery(subquery: SubQuery, depth: int = 1):
    """Extract subquery into a valid SQL statement"""
    return _build_select(
        QueryParams(
            subquery.table,
            subquery.where,
            subquery.cols,
            subquery.limit,
            subquery.orders,  # type: ignore
        ),
        depth=depth,
    )


def _select_onlyparam_parse(data: str | ParsedFn):
    if isinstance(data, str):
        return data
    x = function_extract(data)
    if isinstance(x, tuple):
        return x[0]
    return x


def _setup_hashable(
    condition: Condition, order: Optional[Orders] = None, data: Data | None = None
):
    cond = None
    order_ = None
    data_ = ()
    if isinstance(condition, dict):
        cond = tuple(condition.items())
    if isinstance(condition, list):
        cond = tuple(condition)

    if isinstance(order, tuple):
        order_ = order

    if data:
        data_ = tuple(data.keys())
    return cond, order_, data_


def _setup_limit_patch(table_name: str, condition: str, limit):
    check_one(table_name)
    if not isinstance(limit, int):
        limit = 1
    return f"where rowid in (select rowid from {table_name}\
{' '+condition if condition else ''} limit {limit})"


def _parse_orders(order: CacheOrders):
    if isinstance(order, tuple) and not isinstance(order[0], tuple):
        ord_, order_by = order
        return f"{ord_} {order_by}"
    if isinstance(order, tuple) and isinstance(order[0], tuple):
        return ", ".join(f"{ord_} {order_by}" for ord_, order_by in order)
    raise TypeError("What?", type(order))


def _remove_null(condition: dict[str, Any]) -> dict[str, Any]:
    new = condition.copy()
    for key, value in condition.items():
        if value is Null:
            del new[key]
    if not new:
        raise ValueError(
            "After removing Null sentinel value, new data that would be inserted"
            "/updated returns empty dictionary."
        )
    return new


@lru_cache
def _build_select(query_params: QueryParams, depth: int = 0):
    if depth < 0 or depth >= MAX_SUBQUERY_STACK_LIMIT:
        raise RecursionError("Subquery builder has reached recursion limit of"
                             f"{MAX_SUBQUERY_STACK_LIMIT}")
    check_one(query_params.table_name)
    cond, data = extract_signature(query_params.condition, depth=depth)
    check_iter(query_params.only or ())  # type: ignore
    only_ = "*"
    if query_params.only and isinstance(query_params.only, ParsedFn):
        only_, _ = query_params.only.parse_sql()
    elif isinstance(query_params.only, tuple):
        only_ = f"{', '.join(column_name for column_name in query_params.only)}"
    elif query_params.only != "*" and isinstance(query_params.only, str):
        only_ = check_one(query_params.only)  # type: ignore

    query = f"select {only_} from {query_params.table_name}"
    if cond:
        query += f" {cond}"
    if query_params.order and isinstance(query_params.order, tuple):
        query += f" order by {_parse_orders(query_params.order)}"
    if query_params.limit:
        query += f" limit {query_params.limit}"
    if query_params.offset:
        query += f" offset {query_params.offset}"

    return query, data


@lru_cache
def _build_update(query_params: QueryParams):
    check_one(query_params.table_name)
    cond, data = extract_signature(query_params.condition)
    new_str, updated = build_update_data(query_params.data)  # type: ignore
    query = f"update {query_params.table_name} set {new_str} {cond}"
    if query_params.limit:
        query = query.replace(cond, "")
        query += _setup_limit_patch(query_params.table_name, cond, query_params.limit)
    if query_params.order:
        query += f" order by {_parse_orders(query_params.order)}"
    # ? Require manual intervention to make sure updated is sync as
    # print(query)
    return query, data, updated
    # ? ... combine_keyvals(updated, NEW DATA)
    # ? our cache data only contain keys not values (v0.3.0)


@lru_cache
def _build_delete(query_params: QueryParams):
    check_one(query_params.table_name)
    cond, data = extract_signature(query_params.condition)
    query = f"delete from {query_params.table_name} {cond}"
    if query_params.limit:
        query = query.replace(cond, "")
        query += _setup_limit_patch(query_params.table_name, cond, query_params.limit)
    if query_params.order:
        query += f" order by {_parse_orders(query_params.order)}"
    return query, data


@lru_cache
def _build_insert(table_name: str, data: CacheData):
    check_one(table_name)
    converged = format_paramable(data)
    query = f"insert into {table_name} ({', '.join(val for val in converged)}) \
values ({', '.join(val for val in converged.values())})"
    return query, data


def build_select(  # pylint: disable=too-many-arguments
    table_name: str,
    condition: Condition = None,
    only: tuple[str, ...] | ParsedFn | str | Literal["*"] = "*",
    limit: int = 0,
    offset: int = 0,
    order: Optional[Orders] = None,
) -> tuple[str, dict[str, Any]]:
    """Build select query (this function (backendly) cache!)

    Args:
        table_name (str): Table name
        condition (Condition, optional): Condition to use. Defaults to None.
        only: (OnlyColumn, optional): Select what you want. Default to None.
        limit (int, optional): Limit query (this also limits DB-API 2 `.fetchall`). Defaults to 0.
        offset (int, optional): Offset. Defaults to 0.
        order (Optional[Orders], optional): Order. Defaults to None.

    Returns:
        tuple[str, dict[str, Any]]: query and query data
    """
    cond, order_, _ = _setup_hashable(condition, order)
    params = QueryParams(
        table_name=table_name,
        condition=cond,
        only=only,
        limit=limit,
        offset=offset,
        order=order_,  # type: ignore
    )
    return _build_select(params)


def build_update(
    table_name: str,
    new_data: Data,
    condition: Condition = None,
    limit: int = 0,
    order: Optional[Orders] = None,
) -> tuple[str, dict[str, Any]]:
    """Build update query (once again, this function backendly cache)

    Args:
        table_name (str): Table name
        new_data (Data): New data to update
        condition (Condition, optional): Condition to limit what to update. Defaults to None.
        limit (int, optional): limit chanes. Defaults to 0.
        order (Optional[Orders], optional): What order of change?. Defaults to None.

    Returns:
        tuple[str, dict[str, Any]]: query, query data
    """
    new_data = _remove_null(new_data)
    cond, order_, ndata = _setup_hashable(condition, order, new_data)
    params = QueryParams(
        table_name=table_name,
        condition=cond,
        limit=limit,
        order=order_,  # type: ignore
        data=ndata,
    )
    query, check, updated = _build_update(params)
    return query, check | combine_keyvals(updated, new_data)


def build_delete(
    table_name: str,
    condition: Condition = None,
    limit: int = 0,
    order: Optional[Orders] = None,
) -> tuple[str, dict[str, Any]]:
    """Build delete query

    Args:
        table_name (str): Table name
        condition (Condition, optional): Condition to limit deletion. Defaults to None.
        limit (int, optional): Limit to limit deletion. Defaults to 0.
        order (Optional[Orders], optional): Order. Defaults to None.

    Returns:
        tuple[str, dict[str, Any]]: query, query data
    """

    cond, order_, _ = _setup_hashable(condition, order)
    params = QueryParams(
        table_name, condition=cond, limit=limit, order=order_  # type: ignore
    )
    return _build_delete(params)


def build_insert(table_name: str, data: Data) -> tuple[str, dict[str, Any]]:
    """Build insert query

    Args:
        table_name (str): table name
        data (Data): Data to insert

    Returns:
        tuple[str, dict[str, Any]]: query, query data
    """
    data = _remove_null(data)
    _, _, ndata = _setup_hashable(None, None, data)
    query, _ = _build_insert(table_name, ndata)
    return query, data


__all__ = [
    "ConditionDict",
    "ConditionList",
    "Condition",
    "extract_table",
    "fetch_columns",
    "extract_signature",
    "basic_extract",
    "filter_extraction",
    "build_update_data",
    "format_paramable",
    "combine_keyvals",
    "extract_single_column",
    "extract_table_creations",
    "set_subquery_stack_limit",
]
