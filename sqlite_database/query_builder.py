"""Query Builder"""

from functools import lru_cache
from shlex import shlex
from typing import Any, Iterable, Literal, Optional

from .functions import ParsedFn, _function_extract
from ._utils import check_one, null, check_iter
from .column import Column
from .locals import _SQLITETYPES
from .signature import Signature
from .typings import _MasterQuery, Data, Orders

ConditionDict = dict[str, Signature | ParsedFn | Any]
ConditionList = list[tuple[str, Signature | ParsedFn]]
Condition = ConditionDict | ConditionList | None
CacheCond = tuple[tuple[str, Signature | ParsedFn], ...] | None
CacheOrders = tuple[str, Literal["asc", "desc"]] | ParsedFn | None
CacheData = tuple[str, ...]
OnlyColumn = tuple[str, ...] | ParsedFn
DEFAULT_MAPPINGS = {value: value for value in _SQLITETYPES}


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


def extract_signature(
    filter_: Condition | CacheCond = None, suffix: str = "_check"  # type: ignore
):
    """Extract filter signature."""
    if filter_ is None:
        return "", {}
    if isinstance(filter_, (list, tuple)):
        filter_: ConditionDict = dict(filter_)
    string = "where"
    data: dict[str, Any] = {}
    last = 1
    for key, value in filter_.items():
        if not isinstance(value, Signature):
            value = Signature(value, "==")
        old_data = value.value
        val = (
            Signature(f":{key}{suffix}", value.generate(), value.data)
            if value.value is not null
            else value
        )
        middle = val.generate()
        if val.normal_operator:
            string += f" {key}{middle}{val.value} and"
            last = 4
        if val.is_between:
            vdata: tuple[int, int] = val.data  # type: ignore
            string += f" {key} {middle} {vdata[0]!r} and {vdata[1]!r} and"
        if val.is_like:
            vdata: str = val.data  # type: ignore
            string += f" {key} {middle} {vdata!r} and"
        if val.value is not null:
            data[f"{key}{suffix}"] = old_data

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
    """A function step of table extraction. Used to replace quoted and parens with parameter."""
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
    # ? from now on, it's safe to use , again.
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


def _iterate_etbc_step1(
    columns: Iterable[Column],
    string: str,
    primaries: list[Column],
    foreigns: list[Column],
    maps: dict[str, str],
):
    for column in columns:
        ctype = maps.get(column.type, column.type)
        string += f" {column.name} {ctype}"
        if column.raw_source:
            foreigns.append(column)
        if column.primary:
            primaries.append(column)
        if not column.nullable:
            string += " not null"
        if column.unique:
            string += " unique"
        if column.default:
            string += f" default {repr(column.default)}"
        string += ","
    return string


def extract_table_creations(
    columns: Iterable[Column], type_mappings: dict[str, str] | None = None
):
    """Extract columns classes to sqlite table creation query."""
    maps: dict[str, str] = DEFAULT_MAPPINGS.copy()
    if type_mappings:
        maps.update(type_mappings)
    primaries: list[Column] = []
    foreigns: list[Column] = []
    string = _iterate_etbc_step1(columns, "", primaries, foreigns, maps)

    if primaries:
        string += f" primary key ({', '.join((col.name for col in primaries))}),"
    if not foreigns:
        return string[1:-1]
    for column in foreigns:
        stable, sname = column.source, column.source_column

        string += f" foreign key ({column.name}) references {stable} ({sname})\
 on delete {column.on_delete} on update {column.on_update},"
        # ! This might be a buggy code, i'm not sure yet.
    return string[1:-1]


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

    if isinstance(order, dict):
        order_ = tuple(order.items())

    if data:
        data_ = tuple(data.keys())
    return cond, order_, data_


@lru_cache
def _build_select(
    table_name: str,  # pylint: disable=too-many-arguments
    condition: CacheCond,
    only: OnlyColumn = None,  # type: ignore
    limit: int = 0,
    offset: int = 0,
    order: CacheOrders = None,
):
    check_one(table_name)
    cond, data = extract_signature(condition)
    check_iter(only or ())  # type: ignore
    only_ = "*"
    if only and isinstance(only, ParsedFn):
        only_, _ = only.parse_sql()
    elif only and only != "*":
        only_ = f"{', '.join(column_name for column_name in only)}"

    query = f"select {only_} from {table_name}{' '+cond if cond else ''}"
    if limit:
        query += f" limit {limit}"
    if offset:
        query += f" offset {offset}"
    if order:
        query += " order by"
        for ord_, order_by in order:
            query += f" {ord_} {order_by},"
        query = query[:-1]
    return query, data


@lru_cache
def _build_update(
    table_name: str,
    new_data: CacheData,
    condition: CacheCond = None,
    limit: int = 0,
    order: CacheOrders = None,
):
    check_one(table_name)
    cond, data = extract_signature(condition)
    new_str, updated = build_update_data(new_data)
    query = f"update {table_name} set {new_str} {cond}"
    if limit:
        query += f" limit {limit}"
    if order:
        query += " order by"
        for ord_, order_by in order:
            query += f" {ord_} {order_by},"
        query = query[:-1]
    # ? Require manual intervention to make sure updated is sync as
    return query, data, updated
    # ? ... combine_keyvals(updated, NEW DATA)
    # ? our cache data only contain keys not values (v0.3.0)


@lru_cache
def _build_delete(
    table_name: str,
    condition: CacheCond = None,
    limit: int = 0,
    order: CacheOrders = None,
):
    check_one(table_name)
    cond, data = extract_signature(condition)
    query = f"delete from {table_name} {cond}"
    if limit:
        query += f" limit {limit}"
    if order:
        query += " order by"
        for ord_, order_by in order:
            query += f" {ord_} {order_by}"
        query = query[:-1]
    return query, data


@lru_cache
def _build_insert(table_name: str, data: CacheData):
    check_one(table_name)
    converged = format_paramable(data)
    query = f"insert into {table_name} ({', '.join(val for val in converged)}) \
values ({', '.join(val for val in converged.values())})"
    return query, data


def build_select(
    table_name: str,  # pylint: disable=too-many-arguments
    condition: Condition = None,
    only: tuple[str, ...] | ParsedFn | Literal["*"] = "*",
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
    return _build_select(table_name, cond, only, limit, offset, order_)


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
    cond, order_, ndata = _setup_hashable(condition, order, new_data)
    query, check, updated = _build_update(table_name, ndata, cond, limit, order_)
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
    return _build_delete(table_name, cond, limit, order_)


def build_insert(table_name: str, data: Data) -> tuple[str, dict[str, Any]]:
    """Build insert query

    Args:
        table_name (str): table name
        data (Data): Data to insert

    Returns:
        tuple[str, dict[str, Any]]: query, query data
    """
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
]
