"""User Benchmark

This module is intended as a standing point for anyone who wants to contribute to the project.
Although, any kind of help is appreciated ;)

This module however, is not shipped to the production and only be fetched manually by cloning
the project.

To get started, this module is intended to be imported. So opens up your python interpreter.

-- Details

This module has a database connection from memory which assigned as database. Then, a table person
has columns of text name, integer age, and text gender.

The module also have function fills to fill the table with contents to whatever amount you want.
"""

# Edit this if you get a error.
from sqlite_database import Database, text, integer
from random import randint, choice

database = Database(":memory:")

person = database.create_table("person", [
    text('name'),
    integer('age'),
    text('gender')
])

def fills(amount):
    """Directly filled the table person with pre-generated contents."""
    data = []
    names = ("John Doe", "Felina")
    age = range(100)
    for i in range(amount):
        _pname = choice(names)
        person_name = f"{_pname} #{i}"
        person_age = choice(age)
        person_gender = "M" if _pname == names[0] else 'F'
        data.append({"name": person_name, "age": person_age, "gender": person_gender})
    person.insert_many(data)
    return amount
