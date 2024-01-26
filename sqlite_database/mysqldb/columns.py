"""MySQL columns"""

from ..locals import _SQLITETYPES
from ..column import create_calls

TYPE_LIST = [
    "tinyint",
    "smallint",
    "mediumint",
    "int",
    "integer",
    "bigint",
    "decimal",
    "numeric",
    "float",
    "double",
    "char",
    "varchar",
    "tinytext",
    "text",
    "mediumtext",
    "longtext",
    "date",
    "time",
    "datetime",
    "timestamp",
    "boolean",
    "bool",
    "binary",
    "varbinary",
    "tinyblob",
    "blob",
    "mediumblob",
    "longblob",
    "json",
    "geometry",
    "point",
    "linestring",
    "polygon",
    "bit",
]

TYPE_MAPPINGS = {value: value for value in _SQLITETYPES}
TYPE_MAPPINGS.update({value: value for value in TYPE_LIST})
TYPE_MAPPINGS["integer"] = "int"

for i in TYPE_LIST:
    globals()[i] = create_calls(i, TYPE_LIST)

ALL = TYPE_LIST.copy()
ALL.extend(("TYPE_MAPPINGS", "TYPE_LIST"))
