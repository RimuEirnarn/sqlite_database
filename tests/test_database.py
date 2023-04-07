"""test db"""
# pylint: disable=redefined-outer-name
from io import StringIO
from json import dumps
from os.path import abspath
from types import SimpleNamespace

from pytest import fixture, raises


from sqlite_database import Column, Database, integer, BuilderColumn
from sqlite_database.signature import op
from sqlite_database.errors import TableRemovedError


def parse(data):
    """parse"""
    return dumps(data, indent=2)


config = SimpleNamespace()
file = abspath(f"{__file__}/../../reports.txt")
pstdout = StringIO()

GROUP_BASE = [{
    "id": 0,
    "name": "root"
}, {
    "id": 1,
    "name": "user"
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
        BuilderColumn()
        .integer('id')
        .unique()
        .primary(),
        BuilderColumn()
        .text("username"),
        BuilderColumn()
        .text("role")
        .default("user"),
        BuilderColumn()
        .integer('gid')
        .foreign("groups/id")
    ])
    groups = database.create_table("groups", [
        BuilderColumn()
        .integer('id')
        .primary(),
        BuilderColumn()
        .text('name')
    ])
    groups.insert_many(GROUP_BASE)
    users.insert_many(USER_BASE)


def unload_again(databasepath):
    """unload again"""
    database = Database(databasepath)
    groups = database.table("groups")
    users = database.table("users")
    return database, groups, users


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


@fixture(scope="session")
def databasepath(tmp_path_factory):
    """datahase path"""
    database_path = tmp_path_factory.mktemp("test") / "test.db"
    database = Database(database_path)
    setup_database(database)
    database.close()
    return database_path


config.xdatatabase = None


def test_00_select(databasepath):
    """test 00 select"""
    database, groups, users = unload_again(databasepath)
    config.xdatatabase = database
    assert database is config.xdatatabase
    assert groups.select_one({"id": op == 0}) == GROUP_BASE[0]
    assert groups.select() == GROUP_BASE
    assert users.select_one({"id": op == 0}) == USER_BASE[0]
    assert users.select() == USER_BASE
    assert save_report("00_test", database, groups, users)


def test_01_insert(databasepath):
    """test 01 insert"""
    database, groups, users = unload_again(databasepath)
    assert database is config.xdatatabase
    assert groups.insert_many(GROUP_NEW) is None
    assert users.insert_many(USER_NEW) is None
    assert save_report("01_insert", database, groups, users)


def test_02_update(databasepath):
    """test 02 update"""
    database, groups, users = unload_again(databasepath)
    assert database is config.xdatatabase
    assert groups.update(GROUP_UNEW[0], {"id": op == 2}) == 1
    assert users.update(USER_UNEW[0], {"id": op == 2}) == 1
    assert save_report("02_update", database, groups, users)


def test_03_delete(databasepath):
    """test 03 delete"""
    database, groups, users = unload_again(databasepath)
    assert database is config.xdatatabase
    assert save_report("03_delete", database, groups, users)
    assert groups.delete({"id": op == 3}) == 1
    assert users.delete({"id": op == 3}) == 1


def test_04_finish(databasepath):
    """test 04 finish"""
    database, groups, users = unload_again(databasepath)
    with raises(TableRemovedError):
        assert database is config.xdatatabase
        assert save_report("04_finish", database, groups, users)
        assert database.delete_table("groups") is None
        assert database.delete_table("users") is None
        assert save_report("05_finish", database, groups, users)
    with open(file, "w", encoding="utf-8") as xfile:
        xfile.write(pstdout.getvalue())


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
        print(i)
