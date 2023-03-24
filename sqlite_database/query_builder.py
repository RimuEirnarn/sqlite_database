"""Query Builder"""

from pprint import pprint
from shlex import shlex
from typing import Any, Iterable

from ._utils import check_one, null
from .column import Column
from .locals import _SQLITETYPES
from .signature import op
from .typings import Condition, _MasterQuery


def extract_table(table_creation: str):  # pylint: disable=too-many-locals
    """Extract SQLite table string"""
    data = table_creation[table_creation.find('(')+1:-1]
    cols, upheld = basic_extract(table_creation)
    shlexed = list(shlex(data))
    _, paren_wrap, filtered = filter_extraction(data, shlexed)

    for column_string in filtered.split(','):
        column_shlexed = list(shlex(column_string))
        for tindex, token in enumerate(column_shlexed):
            if token.lower() == "primary":
                next_ = tindex+2
                str_wrap = ''.join(column_shlexed[next_:next_+2])
                if str_wrap.startswith(':wrap'):
                    wrap = paren_wrap[str_wrap]
                else:
                    wrap = str_wrap
                for name in (wrap[1:-1].split(",") if wrap.startswith('(') else wrap.split(',')):
                    upheld[name][4] = True
                continue
            if token.lower() == "foreign":
                next_ = tindex+2
                str_wrap = ''.join(column_shlexed[next_:next_+2])
                if str_wrap.startswith(':wrap'):
                    wrap = paren_wrap[str_wrap]
                else:
                    wrap = str_wrap
                name = wrap[1:-1] if wrap.startswith(
                    '\'') or wrap.startswith('"') else wrap
                name = wrap[1:-1] if wrap.startswith('(') else wrap
                tb_index = next_+3
                tb_col = tb_index+1
                print(dir(), pprint(locals()))
                source_col_str = column_shlexed[tb_col+2][1:-1]
                sources = f"{column_shlexed[tb_index]}/{source_col_str}"
                upheld[name][3] = sources
                upheld[name][2] = True
                if "delete" in column_shlexed:
                    delete_index = column_shlexed.index("delete")
                    upheld[name].append(column_shlexed[delete_index+1])
                if "update" in column_shlexed:
                    uindex = column_shlexed.index("update")
                    upheld[name].append(column_shlexed[uindex+1])

    for _, upheld_column in upheld.items():
        cols.append(Column(*upheld_column))
    return cols


def fetch_columns(_master_query: _MasterQuery):
    """Fetch columns of a table. `_master_query` is originated from select()
    on sqlite_master table"""
    sql = _master_query["sql"]
    return extract_table(sql)


def extract_signature(filter_: Condition = None, suffix: str = '_check'):
    """Extract filter signature."""
    if filter_ is None:
        return "", {}
    string = "where"
    data: dict[str, Any] = {}
    last = 1
    for key, value in filter_.items():
        old_data = value.value if value.value is not null else null
        val = op == f":{key}{suffix}" if value.value is not null else value
        middle = val.generate()
        if val.normal_operator:
            string += f" {key}{middle}{val.value} and"
            last = 4
        if val.is_between:
            vdata: tuple[int, int] = val.data  # type: ignore
            string += f" {key} {middle} {vdata[0]} and {vdata[1]},"
        if val.is_like:
            vdata: str = val.data  # type: ignore
            string += f"{key} {middle} {vdata},"
        if val.value is not null:
            data[f"{key}{suffix}"] = old_data

    return string[:-last], data


def basic_extract(table_creation: str):  # pylint: disable=too-many-locals
    """basic extraction for table"""
    data = table_creation[table_creation.find('(')+1:-1]
    cols = []
    upheld: dict[str, list[Any]] = {}
    for constr in data.split(','):
        name, type_, defaults, sources = "", "", None, ()
        primary = foreign = notnull = unique = False
        base_columns = list(shlex(constr))
        if base_columns[1] not in _SQLITETYPES:
            break  # Other constraint
        name, type_, = base_columns[0], base_columns[1]
        if len(base_columns) == 2:
            # cols.append(Column(name, type_))  # type: ignore
            upheld[name] = [name, type_, False, None, False, False, True, None]
            continue
        for token in base_columns:
            token_lowered = token.lower()
            if token_lowered == "defaults":
                defaults = base_columns[base_columns.index(token)+1]
                defaults = defaults if defaults[0] != "\"" \
                    or defaults[0] != "'" else defaults[1:-1]
            if token_lowered == "primary":
                primary = True
            if token_lowered == "foreign":
                foreign = True
            if token_lowered == "reference":
                tb_index = base_columns.index(token)+1
                tb_col = tb_index+1
                sources = (base_columns[tb_index], base_columns[tb_col][1:-1])
            if token_lowered == "null":
                notnull = base_columns[base_columns.index(
                    token)-1].lower() == 'not'
            if token_lowered == "unique":
                unique = True
        upheld[name] = [name, type_, foreign, f"{sources[0]}/{sources[1]}" if sources else None,
                        primary, unique, not notnull, defaults if defaults else None]
    return cols, upheld


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

    while (index := new_string.find('(')) != -1:
        # ? this attempt to replace all brackets with format-able stuff
        last = new_string.find(')')+1
        selected = new_string[index:last]
        new_string = new_string.replace(
            selected, f":wrap{len(paren_wrap)}")
        paren_wrap[f":wrap{len(paren_wrap)}"] = selected
    # ? from now on, it's safe to use , again.
    return quoted_wrap, paren_wrap, new_string


def build_update_data(data: dict[str, Any], suffix: str = '_set'):
    """Build update data, used to parameterized update data.
    Suffix is used to make sure there's no collisions with others. Use this with caution."""
    string = ""
    that: dict[str, str] = {}
    for key in data:
        check_one(key)
        string += f"{key}=:{key}{suffix}, "
        that[f"{key}{suffix}"] = f":{key}{suffix}"
    return string[:-2], that


def format_paramable(data: dict[str, Any]):
    """Format a data to parameterized data."""
    that: dict[str, str] = {}
    for key in data:
        check_one(key)
        that[key] = f":{key}"
    return that


def combine_keyvals(keydict: dict[str, Any], valuedict: dict[str, Any]):
    """Combine key dictionary with value dictionary. The first dictionary will only
    ignore the values while value dict ignore the keys.
    Mapping[key, _] -> keydict
    Mapping[_, value] -> valuedict"""
    if len(keydict) != len(valuedict):
        raise IndexError("One dictionary is larger. It must be equal.")
    new: dict[str, Any] = {}
    for key0, key1 in zip(keydict, valuedict):
        new[key0] = valuedict[key1]
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


def extract_table_creations(columns: Iterable[Column]):
    """Extract columns classes to sqlite table creation query."""
    string = ''
    primaries: list[Column] = []
    foreigns: list[Column] = []
    for column in columns:
        if column.raw_source:
            foreigns.append(column)
        if column.primary:
            primaries.append(column)
        string += f" {column.name} {column.type}"
        if not column.nullable:
            string += " not null"
        if column.unique:
            string += " unique"
        if column.default:
            string += f" default {repr(column.default)}"
        string += ','

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
