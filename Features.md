# In Depth of Available Features

## Table of contents

1. [More filter](#more-filter)
    1. [Some Constraints](#some-constraints)
2. [Table-related operation](#table-related-operation)
    1. [Select](#select)
    2. [Update](#update)
    3. [Delete](#delete)
    4. [Insert](#insert)
    5. [Functions](#functions)
3. [Database-related operation](#database-related-operation)
    1. [Create Table](#create-table)
    2. [Delete Table](#delete-table)
    3. [Accessing Table](#accessing-table)
    4. [Reset Table](#reset-table)
    5. [Rename Table](#rename-table)
    6. [Check Table](#check-table)
    7. [All Tables](#list-tables-that-have-been-created)
4. [Export](#export)
    1. [Export Table](#export-table)
    2. [Export Database](#export-database)

**Note**: to test these features, make sure you copy and paste this snippet:

```python
from sqlite_database import op
from sqlite_database.operators import eq, like, between
value = 0 # You can use almost anything.
```

For table and database, you can create any dummy database but here's one (assuming you have pasted the above snippet):

```python
from sqlite_database import Database, integer, text
db = Database(":memory:")
table = db.create_table('table', [
    integer('row'),
    text('row2')
])
```

## More filter

Basic

```python
data = table.select({
    "row": op == value
})
```

Basic (new equal) (v0.1.2)

```python
data = table.select({
    'row': value
})
```

List (v0.1.2)

```python
data = table.select([
    eq('row', value)
])
```

Any other variations are just math operators, for the list, operations can be obtained from the `operators` module.

### Some constraints

Like constraint

```python
data = table.select([
    like('row2', 'te%t')
])
```

Between constraint

```python
data = table.select([
    between('row', 0, 10)
])
```

## Table-related operation

### Select

```python
data = table.select({'row': 0})
```

`paginate_select` has the same effect as `select` except that it's paginate.

As it stands, it only covers at-length parameters for an iteration-turn.
This means it loops, selects (based on offset and limit), checks if the length is equal to the length parameter, yields, and increments the offset by the length.

`offset` isn't available as a parameter yet but exists for the `select` method.

**New in v0.4.0**: parameter `only`.

`only` is introduced so that you can select what column you want on a select operation, and use it as usual. However, `only` can also be used on [functions](#functions) too.

So for example:

```python
person = table.select(only=('name', 'age'))
```

is the same as

```sql
select name, age from table
```

On the other hand, a function can also be used in `only`:

```python
table.select(only=count('*'))
```

which achieves the same as

```sql
select COUNT(*) from table
```

#### Crunchy Selection

The result of the select operation is usually a list/tuples of `AttrDict` however, a `crunch` option can be used to 'inverse' it into returning an `AttrDict` where each value are list.

```python
table.select(squash=True)
```

The example will do the trick.

### Update

```python
table.update({
    'row': 1 # What data should change, param name: condition
}, {
    'row': 2 # New data
})
```

You can use `update_one` and `update`. The only difference is that `update_one` has 3 parameters. (yes, excluding the `limit` param.)

### Delete

```python
data = table.delete([
    eq('row', 0)
])
```

### Insert

```python
table.insert({
    'row': 2
})
```

### Functions

You can now use functions on the latest version (from `0.4.0`) however for now, it's limited to only `.select()` queries. However, practically you can use any functions defined.

```python
from sqlite_database.functions import Function
count = Function('COUNT')
person.select(only=count('*'))
```

## Database-related operation

You can use the `cursor` method to use raw SQLite Connection or access the `sql` property to access **the** connection.

For connecting to the database, you can pass any regular keyword args or args for connect (see `sqlite3.connect`)

### Create Table

```python
table = db.create_table('table', [
    integer('row'),
    text('row2')
])
```

### Delete table

```python
db.delete_table('table')
```

### Accessing table

```python
table = db.table('table')
```

### Reset table

```python
table = db.reset_table('table',[
    integer('row'),
    text('row2')
])
```

### Rename table

```python
table = db.rename_table('table', "some_table")
```

### Check table

```python
exists = db.check_table('table')
```

### List tables that have been created

```python
db.tables
```

## Export

You can export the database/table to CSV, for now, import functionality will not be added.

Make sure to add this line

```python
from sqlite_database.csv import to_csv_file, to_csv_string
```

You can use `to_csv_string` rather than `to_csv_file`, all you need is to pass the table or database.

**Note**: The return type for the database is a tuple indicating `(name, csv)`, and by that, `to_csv_file` would make sure that filename passed is a directory and the content will be all table files. E.g: `/path/database/table.csv`

### Export Table

```python
# To String
csv = to_csv_string(db.table("table"))

# To file
to_csv_file(db.table("table"), "table.csv")
```

### Export Database

```python
# To String
csv = to_csv_string(db) # list[(name, csv)]

# To directory
to_csv_file(db.table("table"), "DatabasePath")
```
