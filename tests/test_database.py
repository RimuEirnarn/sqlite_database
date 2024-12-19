"""test db"""
# pylint: disable=redefined-outer-name,invalid-name
from io import StringIO
from json import dumps
from os.path import abspath
from types import SimpleNamespace
from tempfile import mkdtemp
from pathlib import Path
from random import random
from sqlite3 import OperationalError

from pytest import raises


from sqlite_database import Column, Database, integer, text
from sqlite_database.signature import op
from sqlite_database.operators import eq
from sqlite_database.errors import TableRemovedError
from sqlite_database.csv import to_csv_string, to_csv_file
from sqlite_database.utils import crunch
from sqlite_database.functions import Function


def parse(data):
    """parse"""
    return dumps(data, indent=2)

temp_dir = Path(mkdtemp())

config = SimpleNamespace()
file = abspath(f"{__file__}/../reports.txt")
pstdout = StringIO()

count = Function("COUNT")

GROUP_BASE = [{
    "id": 0,
    "name": "root"
}, {
    "id": 1,
    "name": "user"
}]

GROUP_BASE_CRUNCHED = crunch(GROUP_BASE)

GROUP_NAMEBASE = [{
    "name": "root"
}, {
    "name": "user"
}]

USER_NAMEBASE = [{
    "username": 'root',
    'role': 'root'
}]

USER_BASE = [{
    "id": 0,
    "username": "root",
    "role": "root",
    "gid": 0
}, {
    "id": 1,
    "username": "user",
    "role": "user",
    "gid": 1
}]

GROUP_NEW = [{
    "id": 2,
    "name": "test"
}]

USER_NEW = [{
    "id": 2,
    "username": "test",
    "role": "test",
    "gid": 2
}]

GROUP_UNEW = [{
    "id": 3,
    "name": "test1"
}]

USER_UNEW = [{
    "id": 3,
    "username": "test0",
    "role": "test0",
}]

COUNT_DATA = [{
    "item_id": 1,
    "quantity": 50,
    "name": "A"
}, {
    "item_id": 2,
    "quantity": 50,
    "name": "A"

}, {
    "item_id": 3,
    "quantity": 50,
    "name": "A"

}, {
    "item_id": 4,
    "quantity": 50,
    "name": "A"

}]


def setup_database(database: Database):
    """setup database"""
    users = database.create_table("users", [
        Column("id", "integer", unique=True, primary=True),
        Column("username", "text"),
        Column("role", "text", default="user"),
        Column("gid", "integer", foreign=True, foreign_ref="groups/id")
    ])
    groups = database.create_table("groups", [
        Column("id", "integer", primary=True),
        Column("name", "text")
    ])
    groups.insert_many(GROUP_BASE)
    users.insert_many(USER_BASE)


def setup_database_builder(database: Database):
    """Setup database with builder pattern for column"""
    users = database.create_table("users", [
        integer('id').primary(),
        text('username'),
        text('role').default('user'),
        integer('gid').foreign('groups/id')
    ])
    groups = database.create_table("groups", [
        integer('id').primary(),
        text('name')
    ])
    groups.insert_many(GROUP_BASE)
    users.insert_many(USER_BASE)
    database.commit()

def setup_database_fns(database: Database):
    """Setup database used for functions"""
    checkout = database.create_table("checkout", [
        integer("item_id").primary(),
        text("name"),
        integer('quantity')
    ])
    checkout.insert_many(COUNT_DATA)
    database.commit()

database = Database(temp_dir / "test.db") # type: ignore
setup_database_builder(database)
setup_database_fns(database)
users = database.table('users')
groups = database.table('groups')


def save_report(tid, database, grouptb, usertb):
    """save report"""
    master = database.table("sqlite_master")
    print(f">> {tid}", "\n>> master ", parse(master.select()),
                       "\n>> groups", parse(grouptb.select()),
                       "\n>> users", parse(usertb.select()),
          end="\n=======\n",
          file=pstdout
          )
    return True


def test_00_select():
    """test 0000 select"""
    assert groups.select_one({"id": op == 0}) == GROUP_BASE[0]
    assert groups.select() == GROUP_BASE
    assert users.select_one({"id": op == 0}) == USER_BASE[0]
    assert users.select() == USER_BASE
    assert save_report("00_test", database, groups, users)


def test_00_01_select():
    """Test 0001 select"""
    assert groups.select_one([eq('id', 0)]) == GROUP_BASE[0]
    assert groups.select() == GROUP_BASE
    assert users.select_one([eq('id', 0)]) == USER_BASE[0]
    assert users.select() == USER_BASE
    assert save_report("00_test", database, groups, users)


def test_00_02_select():
    """Test 0002 select"""
    assert groups.select_one({'id': 0}) == GROUP_BASE[0]
    assert groups.select() == GROUP_BASE
    assert users.select_one({'id': 0}) == USER_BASE[0]
    assert users.select() == USER_BASE
    assert save_report("00_test", database, groups, users)

def test_00_03_select_only():
    """Test 0003 select only"""
    assert users.select_one({'id': 0}, ('username', 'role')) == USER_NAMEBASE[0]
    assert save_report("00_test", database, groups, users)

def test_00_04_select_crunch():
    """Test 0004 select with crunch"""
    database = Database(":memory:")
    groups = database.table('groups')
    setup_database(database)
    assert groups.select(squash=True) == GROUP_BASE_CRUNCHED

def test_00_05_select_one_only_one_item():
    """Test 0005"""
    database = Database(":memory:")
    groups = database.table('groups')
    setup_database(database)
    assert groups.select_one({'id': 0}, "name") == 'root'

def test_01_insert():
    """test 0100 insert"""
    assert groups.insert_many(GROUP_NEW) is None
    assert users.insert_many(USER_NEW) is None
    users._sql.commit() # pylint: disable=protected-access
    assert not not users.select() # pylint: disable=unnecessary-negation
    assert save_report("01_insert", database, groups, users)


def test_02_01_update():
    """test 0201 update"""
    database = Database(":memory:")
    setup_database_builder(database)
    users = database.table('users')
    groups = database.table('groups')
    assert groups.update({"id": op == 1}, GROUP_UNEW[0]) == 1
    assert users.update({"id": op == 1}, USER_UNEW[0]) == 1
    assert save_report("02_update", database, groups, users)

def test_02_02_update_one():
    """test 0202 update one"""
    database = Database(":memory:")
    setup_database_builder(database)
    users = database.table('users')
    groups = database.table('groups')
    assert groups.update_one({"id": op == 1}, GROUP_UNEW[0]) == 1
    assert users.update_one({"id": op == 1}, USER_UNEW[0]) == 1
    assert save_report("02_update", database, groups, users)

def test_02_03_update_limited_order():
    """Test 0203 update limited with order"""
    database = Database(":memory:")
    setup_database_fns(database)
    checkout = database.table('checkout')
    assert checkout.update({'quantity': 50}, {'quantity': 70}, limit=2, order='asc') == 2 # type: ignore
    assert len(checkout.select({'quantity': 70}, limit=2)) == 2

def test_03_finish():
    """test 0300 finish"""
    with raises(TableRemovedError):
        assert save_report("04_finish", database, groups, users)
        assert database.delete_table("groups") is None
        assert database.delete_table("users") is None
        assert save_report("05_finish", database, groups, users)


def test_04_builder_pattern():
    """Test 0400 builder pattern"""
    database = Database(":memory:")
    setup_database_builder(database)
    users = database.table('users')
    groups = database.table('groups')
    assert users.select() == USER_BASE
    assert groups.select() == GROUP_BASE


def test_05_paginate_select():
    """Test 0500 Pagination select"""
    data = []
    for a, b in zip(range(0, 100), range(1000, 1100)):
        data.append({"x": a, "y": b})

    database = Database(":memory:")
    nums = database.create_table("nums", [
        integer("x"),
        integer("y")
    ])

    nums.insert_many(data)

    for i in nums.paginate_select():
        assert i

def test_06_00_delete():
    """Test 0600 Deletion test"""
    db = Database(":memory:")
    setup_database_builder(db)
    users = db.table('users')
    assert users.delete() == len(USER_BASE)

def test_06_01_delete_condition():
    """Test 0601 Delete based on ID"""
    db = Database(":memory:")
    setup_database_builder(db)
    users = db.table('users')
    assert users.delete({'id': 1}) == 1

def test_06_02_delete_limit():
    """Test 0602 Delete with limit"""
    db = Database(":memory:")
    setup_database_builder(db)
    users = db.table('users')
    assert users.delete(limit=1) == 1

def test_06_03_delete_limit_condition():
    """Test 0603 Delete limit with certain condition"""
    db = Database(":memory:")
    setup_database_fns(db)
    checkout = db.table('checkout')
    assert checkout.delete({'quantity': 50}, limit=2) == 2

def test_06_04_delete_order():
    """Test 0603 Delete limit with certain condition"""
    db = Database(":memory:")
    setup_database_fns(db)
    checkout = db.table('checkout')
    assert checkout.delete({'quantity': 50}, order='asc', limit=2) == 2 # type: ignore

def test_07_00_export_csv():
    """Test 0600 Export to CSV"""
    database = Database(":memory:")
    setup_database(database)
    csv = to_csv_string(database)
    print("test_06_export_csv\n", csv, '\n', file=pstdout, flush=True)
    assert csv


def test_07_01_export_file():
    """Test 0701 Export to CSV file"""
    database = Database(":memory:")
    setup_database(database)
    assert to_csv_file(database.table('users'), temp_dir / "users.csv") # type: ignore

def test_07_02_export_directory():
    """Test 0702 Export to CSV as directory"""
    database = Database(":memory:")
    setup_database(database)
    assert to_csv_file(database, temp_dir / "MemDB") # type: ignore

def test_08_00_function_count():
    """Test 0800 Count(*) usage"""
    database = Database(":memory:")
    setup_database_fns(database)
    counted = count("*")
    data = database.table("checkout").select(only=counted)
    print(data)
    assert data == 4

def test_09_00_select_error():
    db = Database(":memory:")
    setup_database(db)
    groups = db.table('groups')
    with raises(OperationalError):
        groups.select({'nothing': None})

def test_99_99_save_report():
    """FINAL 9999 Save reports"""
    with open(file, "w", encoding="utf-8") as xfile:
        xfile.write(pstdout.getvalue())

def test_100_pity():
    """FINAL"""
    # 99% success rate
    assert random() < 0.99
