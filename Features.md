# In Depth of Available Features

## Table of contents

1. [More filter](#more-filter)
    1. [Some Constraints](#some-constraints)
2. [Table-related operation](#table-related-operation)
    1. [Select](#select)
    2. [Update](#update)
    3. [Delete](#delete)
    4. [Insert](#insert)

**Note**: to test these features, make sure you copy and paste this snippet:

```python
from sqlite_database import op
from sqlite_database.operators import eq, like, between
value = 0 # You can use almost anything.
```

For table and database, you can create any dummy database but here's one (assuming you have paste above snippet):

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

Any other variations are just math operators, for list, operations can be obtained from `operators` module.

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

[here](#more-filter)

`paginate_select` have same effect as `select` exxcept that it's paginate.

As it stands, it only covers at length parameters for a iteration-turn.
Meaning it loops, select (base on offset and limit), check if length is equal to length parameter, yield, and increment the offset by the length.

`offset` isn't available as parameter yet but exists for `select` method.

### Update

```python
table.update({
    'row': 2
}, {
    'row': 1
})
```

You can use `update_one` and `update`. The only difference is that, `update_one` have 3 parameters. (yes, excluding `limit` param.)

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

## Database-related operation

You can use `cursor` method to actually use raw SQLite Connection, or access the `sql` property to access **the** connection.

For connecting to database, you can pass any regular keyword args or args for connect (see `sqlite3.connect`)
### Create Table

At the top of this file should have something named `create_table`

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