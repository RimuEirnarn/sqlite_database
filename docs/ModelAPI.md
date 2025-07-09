# Introduction to ModelAPI

*NOTICE!*: Model API has very different structures compared to TableAPI!

## Table of Contents

- [Introduction to ModelAPI](#introduction-to-modelapi)
  - [Table of Contents](#table-of-contents)
  - [Using ModelAPI](#using-modelapi)
    - [Bootstrapping](#bootstrapping)
    - [Creating a model](#creating-a-model)
    - [Spinning it up](#spinning-it-up)
      - [CREATE](#create)
      - [READ](#read)
        - [`.all`, `.first`, `.one`](#all-first-one)
        - [`.where`](#where)
      - [UPDATE](#update)
      - [DELETE](#delete)
    - [Lil' example?](#lil-example)

---

## Using ModelAPI

The ModelAPI consist of Model-based schema, useful if you've used to Laravel Eloquent.

### Bootstrapping

In `db.py`:

```py
from sqlite_database import Database

db = Database(":memory:")
```

### Creating a model

In `model/notes.py`:

```py
from uuid import uuid4
from sqlite_database import model, BaseModel, Primary
from ..db import db

@model(db)
class Notes(BaseModel):
    __schema__ = (Primary('id'),)
    __auto_id__ = lambda: str(uuid4())

    id: str
    title: str
    content: str
```

This way, we have a nice little model. The `__schema__` initiate what part is `Unique()`, `Primary()`, and `Foreign()` whereas `__auto_id__` creates `id` (or any primary key) for you.

### Spinning it up

#### CREATE

A simple example would be:

Somewhere in `main.py`:

```py
title = input('title: ')
content = input("content: ")
Notes.create(title=title, content=content)
```

It'll be created right away, oneline.

#### READ

There's abundant amount of method to read from your model.

##### `.all`, `.first`, `.one`

Let's spin it up!

```py
Notes.all() # This will return ALL notes
Notes.first(id=id) # Returns any first instance found.
Notes.one(id=id) # Returns one and ONLY one data. If a Note is supplied and returns multiple data, it will fail.
```

##### `.where`

But above methods doesn't give you enough control over what will return.

Let's see how `.where()` behave:

```py
title = input("title: ")
note = Notes.where(title=title).fetch_one() # Will return our lil note
Notes.where().limit(5).fetch() # Will return 5 Notes
Notes.where().offset(5).fetch() # Will return every Notes except first 5.
Notes.where().count() # Will return how much Notes do we have
```

#### UPDATE

Suppose we have a note instance lying around, updating it is as easy as inserting

```py
note = Notes.first(id=id)
title = input('title')
content = input('cotnent')
note.update(title=title, content=content)
```

#### DELETE

Let's just use the same format as before, but we need to rename it.

```py
note = Notes.first(id=id)
note.delete()
```

### Lil' example?

```py
from enum import IntEnum
from uuid import uuid4
from sqlite_database import Database, model, BaseModel, Primary

db = Database(":memory:")

@model(db)
class Notes(BaseModel):
    __schema__ = (Primary('id'),)
    __auto_id__ = lambda: str(uuid4())

    id: str
    title: str
    content: str

def display():
    print('-'*3)
    for note in Notes.all():
        print(f"ID      : {note.id}")
        print(f"Title   : {note.title}")
        print(f"Content : {note.content}")
        print("-"*3)

def create():
    title = input("Title: ")
    content = input("Content: ")

    Notes.create(title=title, content=content)

def update():
    note_id = input('ID: ')
    title = input('title: ')
    content = input('content: ')

    note = Notes.first(id=note_id)
    if note:
        note.update(title=title, content=content)
        return
    print(f"Note {note_id} not found!")

def delete():
    note_id = input('ID: ')
    note= Notes.first(id=note_id)
    if note:
        note.delete()
        return
    print(f"Note {note_id} not found!")

class CMD(IntEnum):
    DISPLAY = 1
    CREATE = 2
    UPDATE = 3
    DELETE = 4
    EXIT = 5

def main():
    while True:
        print('-'*8)
        print('1. Display all notes')
        print('2. Create a note')
        print('3. Update a note')
        print('4. Delete a note')
        print('5. Exit (CTRL+C)')
        try:
            cmd = int(input("Enter command: "))

            if cmd == CMD.DISPLAY:
                display()
            if cmd == CMD.CREATE:
                create()
            if cmd == CMD.UPDATE:
                update()
            if cmd == CMD.DELETE:
                delete()
            if cmd == CMD.EXIT:
                return
        except KeyboardInterrupt:
            return
        except Exception as exc:
            print(f"{type(exc).__name__}: {exc!s}")

if __name__ == '__main__':
    main()
```
