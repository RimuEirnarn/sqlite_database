# SQLite Database

This is a simple wrapper for Python's built-in sqlite package. It uses simple API to interact with the database in a NoSQL-like fashion.

## Table of content

- [SQLite Database](#sqlite-database)
  - [Table of content](#table-of-content)
  - [In Depth of Available Features](#in-depth-of-available-features)
    - [Available Filters](#available-filters)
    - [Available Constraints](#available-constraints)
    - [Table-related operation](#table-related-operation)
      - [Select](#select)
        - [Select Common Params](#select-common-params)
        - [Select Methods](#select-methods)
      - [Update](#update)
      - [Delete](#delete)
      - [Insert](#insert)
      - [Functions](#functions)
    - [Database-related operation](#database-related-operation)
      - [Create Table](#create-table)
      - [Delete table](#delete-table)
      - [Accessing table](#accessing-table)
      - [Reset table](#reset-table)
      - [Rename table](#rename-table)
      - [Check table](#check-table)
      - [List tables that have been created](#list-tables-that-have-been-created)
    - [Export](#export)
      - [Export Table](#export-table)
      - [Export Database](#export-database)

## In Depth of Available Features

**Note**: To test these features, make sure you copy and paste this snippet:

```python
from sqlite_database import op
from sqlite_database.operators import eq, like, between
value = 0 # You can use almost anything.
```

For table and database, you can create any dummy database, but here's one (assuming you have pasted the above snippet):

```python
from sqlite_database import Database, integer, text
from sqlite_database import this
db = Database(":memory:")
my_table = db.create_table('my_table', [
    integer('row'),
    text('row2')
])
```

### Available Filters

`this`:

```python
data = table.select({
    "row": this == value
})
```

Key-Value:

```python
data = table.select({
    'row': value
})
```

List of functions:

```python
data = table.select([
    eq('row', value)
])
```

Any other variations are just math operators. For the list, operations can be obtained from the `operators` module.

### Available Constraints

Like constraint:

```python
data = table.select([
    like('row2', 'te%t')
])
```

Between constraints:

```python
data = table.select([
    between('row', 0, 10)
])
```

### Table-related operation

#### Select

To retrieve contents of a table, you can use `.select*` methods such as `.paginate_select`, `.select`, and `.select_one`. See [Select Methods](#select-methods).

##### Select Common Params

`offset`: returns at specific position

`only`: you can use `only` to select which columns you want to return and use it as usual. However, `only` can also be used on [functions](#functions) too.

So, for example:

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

`order`: you can change the return order from `asc` and `desc`.

`squash`: The result of the select operation is usually a list/tuples of `Row` however, a `squash` option can be used to 'inverse' it into returning an `Row` where each value are list.

```python
table.select(squash=True)
```

The example will do the trick.

##### Select Methods

`.paginate_select`: yields a selection page, useful when there's a ton of data and you want to limit how much it returns at a time.

As it stands, it only covers length parameters for an iteration turn.
This means it loops, selects (based on offset and limit), checks if the length is equal to the length parameter, yields, and increments the offset by the length.

Example:

```python
several_people = table.paginate_select(
    {"age": this >= 20}, # Select people with age more or equal than 20
    length=20, # Each page has 20 columns
)

for page in several_people:
    print(page)
```

There's also `page` param so you can skip directly to which page to return.

`.select`: selects, described in [Select](#select)

Example:

```python
persons = table.select() # This returns everything
persons_age = table.select(only=('age',)) # This returns everything but only contains the 'age' column.
```

See [Select Common Params](#select-common-params)

`.select_one`: Like `.select()` but returns one item (`Row`)

#### Update

To change columns on matching `conditions`, use either `update()` or `update_one`. `update_on` updates specifically one item.

```python
table.update({
    'row': 1 # What data should change, param name: condition
}, {
    'row': 2 # New data
})
```

#### Delete

You can delete row(s).

```python
data = table.delete([
    eq('row', 0)
])
```

Most of the parameters are `conditions`, `limit`, and `order`. `.delete` also has `.delete_one`

#### Insert

To push data, you can use `.insert`

```python
table.insert({
    'row': 2
})
```

use `.insert_multiple` if your data has many things.

#### Functions

You can now use functions. However, for now, it's limited to only `.select()` queries. However, practically, you can use any functions defined.

```python
from sqlite_database.functions import Function
count = Function('COUNT')
person.select(only=count('*'))
```

### Database-related operation

You can use the `cursor` method to use raw SQLite Connection or access the `sql` property to access the connection.

For connecting to the database, you can pass any regular keyword args or args for connect (see [`sqlite3.connect`](https://docs.python.org/3/library/sqlite3.html#sqlite3.connect))

#### Create Table

You can create a table, yes. By default, available types defined are `real`, `text`, `integer`, and `blob`

```python
table = db.create_table('table', [
    integer('row'),
    text('row2')
])
```

#### Delete table

```python
db.delete_table('table')
```

#### Accessing table

```python
table = db.table('table')
```

#### Reset table

```python
table = db.reset_table('table',[
    integer('row'),
    text('row2')
])
```

#### Rename table

```python
table = db.rename_table('table', "some_table")
```

#### Check table

```python
if db.check_table('table'): # Table exists
    # do something
```

#### List tables that have been created

```python
db.tables
```

### Export

You can export the database/table to CSV. For now, import functionality will not be added.

Make sure to add this line

```python
from sqlite_database.csv import to_csv_file, to_csv_string
```

You can use `to_csv_string` rather than `to_csv_file`, all you need is to pass the table or database.

**Note**: The return type for the database is a tuple indicating `(name, csv)`, and by that, `to_csv_file` would make sure that filename passed is a directory and the content will be all table files. E.g: `/path/database/table.csv`

#### Export Table

```python
# To String
csv = to_csv_string(db.table("table"))

# To file
to_csv_file(db.table("table"), "table.csv")
```

#### Export Database

```python
# To String
csv = to_csv_string(db) # list[(name, csv)]

# To directory
to_csv_file(db.table("table"), "DatabasePath")
```
