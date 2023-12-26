"""test db"""
# pylint: disable=redefined-outer-name,invalid-name
from io import StringIO
from json import dumps
from os.path import abspath
from types import SimpleNamespace
from tempfile import mkdtemp
from pathlib import Path

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

def setup_database_fns(database: Database):
    """Setup database used for functions"""
    checkout = database.create_table("checkout", [
        integer("item_id").primary(),
        text("name"),
        integer('quantity')
    ])
    checkout.insert_many(COUNT_DATA)

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
    """test 00 select"""
    assert groups.select_one({"id": op == 0}) == GROUP_BASE[0]
    assert groups.select() == GROUP_BASE
    assert users.select_one({"id": op == 0}) == USER_BASE[0]
    assert users.select() == USER_BASE
    assert save_report("00_test", database, groups, users)


def test_001_select():
    """Test 001 select"""
    assert groups.select_one([eq('id', 0)]) == GROUP_BASE[0]
    assert groups.select() == GROUP_BASE
    assert users.select_one([eq('id', 0)]) == USER_BASE[0]
    assert users.select() == USER_BASE
    assert save_report("00_test", database, groups, users)


def test_002_select():
    """Test 002 select"""
    assert groups.select_one({'id': 0}) == GROUP_BASE[0]
    assert groups.select() == GROUP_BASE
    assert users.select_one({'id': 0}) == USER_BASE[0]
    assert users.select() == USER_BASE
    assert save_report("00_test", database, groups, users)

def test_003_select_only():
    """Test 003 select only"""
    assert groups.select_one({"id": 0}, ('name',)) == GROUP_NAMEBASE[0]
    assert users.select_one({'id': 0}, ('username', 'role')) == USER_NAMEBASE[0]
    assert save_report("00_test", database, groups, users)

def test_004_select_crunch():
    """Test 004 select with crunch"""
    database = Database(":memory:")
    groups = database.table('groups')
    setup_database(database)
    assert groups.select(squash=True) == GROUP_BASE_CRUNCHED

def test_01_insert():
    """test 01 insert"""
    assert groups.insert_many(GROUP_NEW) is None
    assert users.insert_many(USER_NEW) is None
    assert save_report("01_insert", database, groups, users)


def test_02_update():
    """test 02 update"""
    assert groups.update({"id": op == 2}, GROUP_UNEW[0]) == 1
    assert users.update({"id": op == 2}, USER_UNEW[0]) == 1
    assert save_report("02_update", database, groups, users)


def test_03_delete():
    """test 03 delete"""
    assert save_report("03_delete", database, groups, users)
    assert groups.delete({"id": op == 3}) == 1
    assert users.delete({"id": op == 3}) == 1


def test_04_finish():
    """test 04 finish"""
    with raises(TableRemovedError):
        assert save_report("04_finish", database, groups, users)
        assert database.delete_table("groups") is None
        assert database.delete_table("users") is None
        assert save_report("05_finish", database, groups, users)


def test_05_builder_pattern():
    """Test 05 builder pattern"""
    database = Database(":memory:")
    setup_database_builder(database)
    users = database.table('users')
    groups = database.table('groups')
    assert users.select() == USER_BASE
    assert groups.select() == GROUP_BASE


def test_06_paginate_select():
    """Pagination select"""
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

def test_07_export_csv():
    """Export to CSV"""
    database = Database(":memory:")
    setup_database(database)
    csv = to_csv_string(database)
    print("test_06_export_csv\n", csv, '\n', file=pstdout, flush=True)
    assert csv


def test_08_export_file():
    """Export to CSV file"""
    database = Database(":memory:")
    setup_database(database)
    assert to_csv_file(database.table('users'), temp_dir / "users.csv") # type: ignore

def test_09_export_directory():
    """Export to CSV as directory"""
    database = Database(":memory:")
    setup_database(database)
    assert to_csv_file(database, temp_dir / "MemDB") # type: ignore

def test_10_0_function_count():
    """Count(*) usage"""
    database = Database(":memory:")
    setup_database_fns(database)
    counted = count("*")
    data = database.table("checkout").select(only=counted)
    print(data)
    assert data == 4

def test_99_save_report():
    """Save reports"""
    with open(file, "w", encoding="utf-8") as xfile:
        xfile.write(pstdout.getvalue())
