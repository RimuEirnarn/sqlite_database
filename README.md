# SQLite Database

SQLite Database is a weird wrapper for SQLite Connection.

## Overview

Connect to a connection:

```python
from sqlite_database import Database, text, integer, op
conn = Database(":memory:")
```

Create a table

```python
users = conn.create_table("users", [
    text("name"),
    integer("id").primary()
])
```

Insert a data to table

```python
users.insert_one({
    "name": 'name',
    'id': 3
})
```

Select a data from table

```python
data = users.select({
    "id": 3
})
```

Update a data from table

```python
users.update({
    "name": "test"
}, {
    "id": 3
})
```

Delete a data from table

```python
users.delete({
    "id": 3
})
```

## Installation

Using pip and tag this repo should suffice, just get the raw archive, and it'll be done.
