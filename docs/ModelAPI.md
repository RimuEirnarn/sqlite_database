# ModelAPI: Lightweight ORM for SQLite

> **Note:** `ModelAPI` uses a model-centric approach inspired by Laravel's Eloquent ORM. It differs significantly from `TableAPI`. Use the one that fits your style and project structure best.

---

## 📚 Table of Contents

- [ModelAPI: Lightweight ORM for SQLite](#modelapi-lightweight-orm-for-sqlite)
  - [📚 Table of Contents](#-table-of-contents)
  - [🏁 Getting Started](#-getting-started)
    - [Installation](#installation)
    - [Database Setup](#database-setup)
  - [🧱 Defining Models](#-defining-models)
    - [`__schema__` and Fields](#__schema__-and-fields)
    - [`__auto_id__`](#__auto_id__)
  - [🔧 CRUD Operations](#-crud-operations)
    - [✅ Create](#-create)
    - [🔍 Read](#-read)
      - [`all()`, `first()`, `one()`](#all-first-one)
      - [`where()` Queries](#where-queries)
    - [📝 Update](#-update)
    - [🗑 Delete](#-delete)
  - [⚙️ Practical CLI Example](#️-practical-cli-example)
  - [🧠 Best Practices](#-best-practices)
  - [⚠️ Common Pitfalls](#️-common-pitfalls)

---

## 🏁 Getting Started

### Installation

Assuming you didn't have `sqlite_database` in your library, install it with:

```bash
pip install sqlite-database
```

> Otherwise, just make sure it's available in your project path.

### Database Setup

Initialize  SQLite database:

```py
# db.py
from sqlite_database import Database

db = Database("notes.db")  # or ":memory:" for in-memory DB
```

---

## 🧱 Defining Models

Define your model using the `@model(db)` decorator and inherit from `BaseModel`.

### `__schema__` and Fields

Declare your schema using `Primary`, `Unique`, or `Foreign` field descriptors:

```py
# model/notes.py
from uuid import uuid4
from sqlite_database import model, BaseModel, Primary
from db import db

@model(db)
class Notes(BaseModel):
    __schema__ = (Primary('id'),)

    id: str
    title: str
    content: str
```

### `__auto_id__`

Optionally, auto-generate IDs (especially useful for `UUID`):

```py
@model(db)
class Notes(BaseModel):
    ...

    __auto_id__ = lambda: str(uuid4())

    ...
```

---

## 🔧 CRUD Operations

### ✅ Create

```py
Notes.create(title="Meeting", content="Discuss roadmap")
```

Input-based example:

```py
title = input("Title: ")
content = input("Content: ")
Notes.create(title=title, content=content)
```

---

### 🔍 Read

#### `all()`, `first()`, `one()`

```py
Notes.all()              # Returns all notes
Notes.first(id="abc")    # Returns first match or None
Notes.one(id="abc")      # Returns exactly one; errors if multiple
```

#### `where()` Queries

The `where()` method returns a query builder with powerful chaining:

```py
Notes.where(title="Roadmap").fetch_one()
Notes.where().limit(5).fetch()
Notes.where().offset(5).fetch()
Notes.where().count()
```

---

### 📝 Update

```py
note = Notes.first(id="abc")
if note:
    note.update(title="Updated", content="Updated content")
```

---

### 🗑 Delete

```py
note = Notes.first(id="abc")
if note:
    note.delete()
```

---

## ⚙️ Practical CLI Example

A complete CLI that interacts with the `Notes` model:

```py
# cli.py
from model.notes import Notes
from enum import IntEnum

class CMD(IntEnum):
    DISPLAY = 1
    CREATE = 2
    UPDATE = 3
    DELETE = 4
    EXIT = 5

def display():
    print("---")
    for note in Notes.all():
        print(f"ID: {note.id}\nTitle: {note.title}\nContent: {note.content}\n---")

def create():
    Notes.create(title=input("Title: "), content=input("Content: "))

def update():
    note = Notes.first(id=input("ID: "))
    if note:
        note.update(title=input("Title: "), content=input("Content: "))
    else:
        print("Note not found.")

def delete():
    note = Notes.first(id=input("ID: "))
    if note:
        note.delete()
    else:
        print("Note not found.")

def main():
    while True:
        print("1. Display\n2. Create\n3. Update\n4. Delete\n5. Exit")
        try:
            cmd = int(input("Select: "))
            if cmd == CMD.DISPLAY: display()
            elif cmd == CMD.CREATE: create()
            elif cmd == CMD.UPDATE: update()
            elif cmd == CMD.DELETE: delete()
            elif cmd == CMD.EXIT: break
        except Exception as e:
            print(f"{type(e).__name__}: {e}")

if __name__ == '__main__':
    main()
```

---

## 🧠 Best Practices

- ✅ Always define `__schema__` clearly; include all primary, foreign, and unique constraints.
- ✅ Use `__auto_id__` to generate consistent primary keys, especially UUIDs.
- ✅ Keep models slim—business logic should live outside models.
- ✅ Use `.where().count()` to avoid expensive `.all()` calls when counting.
- ✅ Use `.one()` only when you're sure the result is exactly one row.

---

## ⚠️ Common Pitfalls

- ❌ Forgetting to include `@model(db)` — your class won't be registered.
- ❌ Using `.one()` when multiple records match — it will throw an exception.
- ❌ Not calling `fetch()` or `fetch_one()` after `.where()` — query won't execute.
- ❌ Assuming `create()` returns an object — it doesn’t.

---
