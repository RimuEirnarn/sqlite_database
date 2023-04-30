# TODO

**NOTE**: This TODO need to be written in markdown. use `[ ]` or `[x]` to mark todos

**High velocity** is required but make sure to do it with low overhead.

## SQLite API

What API should we bring? These todo's is for simplification; you can do anything with `Database.sql` property

- [ ] sqlite function support
- [ ] sqlite aggregate function support
- [ ] sqlite window function support
- [ ] sqlite collation support
- [ ] sqlite pragma
- [ ] sqlite branching subquery (??)
- [ ] sqlite 'as' keyword (??)
- [ ] sqlite non-table operation
- [x] sqlite select data crunching[^1] by using Database config option (crunch=True)
- [x] sqlite select 'only' data. Instead of using `select *`, we should also have `only`. Bring up few data than select everything.[^2]
- [x] Provide caching functions; not to cache sql returns but sql query, etc.[^3]

## Other functionality

The functionality here is outside of sqlite features such as export and import.

- [ ] YAML/JSON/TOML/CUSTOM scheme/table include
- [x] CSV Export
- [ ] CSV Import
- [ ] Other method of Import

[^1]: The term data crunching is when `select*` is used, typically the functions returns list of `AttrDict`, by using `crunch=True`, the return value should be `AttrDict[str, tuple[Any]]`
[^2]: If `only` parameter is specified to 1, we should return `tuple[Any, ...]` instead of `list[AttrDict[str, Any]]` or `AttrDict[str, Any]`
[^3]: Caching should **NOT** cache query data! Provide using `combine_keyvals` to create named params
