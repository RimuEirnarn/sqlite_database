"""test db"""

# pylint: disable=redefined-outer-name,invalid-name
from io import StringIO
from json import dumps
from os.path import abspath
from types import SimpleNamespace
from tempfile import mkdtemp
from pathlib import Path
from random import randint, random
from sqlite3 import OperationalError
from uuid import UUID, uuid4
from pytest import raises


from sqlite_database._debug import STATE
from sqlite_database import Column, Database, integer, text, Null
from sqlite_database.models import Primary, Unique, model, BaseModel, Foreign, CASCADE
from sqlite_database.models.errors import ValidationError, NoDataReturnedError
from sqlite_database.models.mixin import ChunkableMixin, ScopeMixin
from sqlite_database.signature import op
from sqlite_database.operators import eq, in_, this
from sqlite_database.errors import TableRemovedError, CuteDemonLordException
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

GROUP_BASE = [{"id": 0, "name": "root"}, {"id": 1, "name": "user"}]

GROUP_BASE_CRUNCHED = crunch(GROUP_BASE)

GROUP_NAMEBASE = [{"name": "root"}, {"name": "user"}]

USER_NAMEBASE = [{"username": "root", "role": "root"}]

USER_BASE = [
    {"id": 0, "username": "root", "role": "root", "gid": 0},
    {"id": 1, "username": "user", "role": "user", "gid": 1},
]

GROUP_NEW = [{"id": 2, "name": "test"}]

USER_NEW = [{"id": 2, "username": "test", "role": "test", "gid": 2}]

GROUP_UNEW = [{"id": 3, "name": "test1"}]

USER_UNEW = [
    {
        "id": 3,
        "username": "test0",
        "role": "test0",
    }
]

COUNT_DATA = [
    {"item_id": 1, "quantity": 50, "name": "A"},
    {"item_id": 2, "quantity": 50, "name": "A"},
    {"item_id": 3, "quantity": 50, "name": "A"},
    {"item_id": 4, "quantity": 50, "name": "A"},
]


def setup_database(database: Database):
    """setup database"""
    users = database.create_table(
        "users",
        [
            Column("id", "integer", unique=True, primary=True),
            Column("username", "text"),
            Column("role", "text", default="user"),
            Column("gid", "integer", foreign=True, foreign_ref="groups/id"),
        ],
    )
    groups = database.create_table(
        "groups", [Column("id", "integer", primary=True), Column("name", "text")]
    )
    groups.insert_many(GROUP_BASE)
    users.insert_many(USER_BASE)


def setup_database_builder(database: Database):
    """Setup database with builder pattern for column"""
    users = database.create_table(
        "users",
        [
            integer("id").primary(),
            text("username"),
            text("role").default("user"),
            integer("gid").foreign("groups/id"),
        ],
    )
    groups = database.create_table("groups", [integer("id").primary(), text("name")])
    groups.insert_many(GROUP_BASE)
    users.insert_many(USER_BASE)
    database.commit()


def setup_database_fns(database: Database):
    """Setup database used for functions"""
    checkout = database.create_table(
        "checkout", [integer("item_id").primary(), text("name"), integer("quantity")]
    )
    checkout.insert_many(COUNT_DATA)
    database.commit()


def setup_orderable(database: Database):
    """Setup database with order-able data"""
    items = database.create_table("items", [text("name"), integer("quantity")])
    items.insert_many([{"name": "a", "quantity": a} for a in range(100)])
    database.commit()


def setup_model_api(database: Database):
    # pylint: disable=missing-class-docstring
    """Setup Model API Users/Posts"""

    @model(database)
    class Users(BaseModel):
        __schema__ = (Primary("id"), Unique("username"))
        id: str
        username: str
        is_active: bool = True

    @model(database)
    class Posts(BaseModel):
        __schema__ = (Primary("id"),
                      Foreign("user_id", Users)\
                              .on_delete(CASCADE)\
                              .on_update(CASCADE))
        id: str
        user_id: str
        title: str
        content: str

    return Users, Posts


database = Database(temp_dir / "test.db")  # type: ignore
setup_database_builder(database)
setup_database_fns(database)
users = database.table("users")
groups = database.table("groups")


def save_report(tid, database, grouptb, usertb):
    """save report"""
    master = database.table("sqlite_master")
    print(
        f">> {tid}",
        "\n>> master ",
        parse(master.select()),
        "\n>> groups",
        parse(grouptb.select()),
        "\n>> users",
        parse(usertb.select()),
        end="\n=======\n",
        file=pstdout,
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
    assert groups.select_one([eq("id", 0)]) == GROUP_BASE[0]
    assert groups.select() == GROUP_BASE
    assert users.select_one([eq("id", 0)]) == USER_BASE[0]
    assert users.select() == USER_BASE
    assert save_report("00_test", database, groups, users)


def test_00_02_select():
    """Test 0002 select"""
    assert groups.select_one({"id": 0}) == GROUP_BASE[0]
    assert groups.select() == GROUP_BASE
    assert users.select_one({"id": 0}) == USER_BASE[0]
    assert users.select() == USER_BASE
    assert save_report("00_test", database, groups, users)

    assert users.select_one({"id": 0}, ("username", "role")) == USER_NAMEBASE[0]
    assert save_report("00_test", database, groups, users)


def test_00_04_select_crunch():
    """Test 0004 select with crunch"""
    database = Database(":memory:")
    setup_database(database)
    groups = database.table("groups")
    assert groups.select(flatten=True) == GROUP_BASE_CRUNCHED


def test_00_05_select_one_only_one_item():
    """Test 0005"""
    database = Database(":memory:")
    setup_database(database)
    groups = database.table("groups")
    assert groups.select_one({"id": 0}, "name") == "root"


def test_00_06_select_order_by():
    """Test 0006 Select order by"""
    database = Database(":memory:")
    setup_orderable(database)
    items = database.table("items")
    first_high = items.select(what="quantity", limit=3, order=("quantity", "asc"))
    first_low = items.select(what="quantity", limit=3, order=("quantity", "desc"))
    assert first_high == [0, 1, 2]
    assert first_low == [99, 98, 97]


def test_00_07_select_subquery():
    """Test 0007 Select with subqueries"""
    db = Database(":memory:")
    notes = db.create_table("notes", [text("id").primary(), text("content")])
    notes.insert({"id": "0", "content": "abc"})
    data = notes.select_one({"id": notes.subquery({"id": "0"}, "id", limit=1)})
    assert data is not None


def test_01_insert():
    """test 0100 insert"""
    assert groups.insert_many(GROUP_NEW) is None
    assert users.insert_many(USER_NEW) is None
    users._sql.commit()  # pylint: disable=protected-access
    assert not not users.select()  # pylint: disable=unnecessary-negation
    assert save_report("01_insert", database, groups, users)


def test_01_01_insert_with():
    """Test 0101 insert in with-statement"""
    db = Database(":memory:")
    table = db.create_table("a", [text("name")])
    try:
        with table:
            table.insert({"name": "Admin"})
            raise CuteDemonLordException(
                "Haha, i'm cute demon lord and I cast [Insert Dispell]"
            )
    except CuteDemonLordException:
        pass
    assert table.select() == []


def test_01_02_insert_empty():
    """Test 0101 insert in with-statement"""
    db = Database(":memory:")
    table = db.create_table("a", [text("name")])
    with raises(ValueError):
        table.insert({"name": Null})


def test_02_01_update():
    """test 0201 update"""
    database = Database(":memory:")
    setup_database_builder(database)
    users = database.table("users")
    groups = database.table("groups")
    assert groups.update({"id": op == 1}, GROUP_UNEW[0]) == 1
    assert users.update({"id": op == 1}, USER_UNEW[0]) == 1
    assert save_report("02_update", database, groups, users)


def test_02_02_update_one():
    """test 0202 update one"""
    database = Database(":memory:")
    setup_database_builder(database)
    users = database.table("users")
    groups = database.table("groups")
    assert groups.update_one({"id": op == 1}, GROUP_UNEW[0]) == 1
    assert users.update_one({"id": op == 1}, USER_UNEW[0]) == 1
    assert save_report("02_update", database, groups, users)


def test_02_03_update_limited_order():
    """Test 0203 update limited with order"""
    database = Database(":memory:")
    setup_database_fns(database)
    checkout = database.table("checkout")
    assert (
        checkout.update({"quantity": 50}, {"quantity": 70}, limit=2) == 2
    )  # type: ignore
    assert len(checkout.select({"quantity": 70}, limit=2)) == 2


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
    users = database.table("users")
    groups = database.table("groups")
    assert users.select() == USER_BASE
    assert groups.select() == GROUP_BASE


def test_05_paginate_select():
    """Test 0500 Pagination select"""
    data = []
    for a, b in zip(range(0, 100), range(1000, 1100)):
        data.append({"x": a, "y": b})

    database = Database(":memory:")
    nums = database.create_table("nums", [integer("x"), integer("y")])

    nums.insert_many(data)

    for i in nums.paginate_select():
        assert i


def test_06_00_delete():
    """Test 0600 Deletion test"""
    db = Database(":memory:")
    setup_database_builder(db)
    users = db.table("users")
    assert users.delete() == len(USER_BASE)


def test_06_01_delete_condition():
    """Test 0601 Delete based on ID"""
    db = Database(":memory:")
    setup_database_builder(db)
    users = db.table("users")
    assert users.delete({"id": 1}) == 1


def test_06_02_delete_limit():
    """Test 0602 Delete with limit"""
    db = Database(":memory:")
    setup_database_builder(db)
    users = db.table("users")
    assert users.delete(limit=1) == 1


def test_06_03_delete_limit_condition():
    """Test 0603 Delete limit with certain condition"""
    db = Database(":memory:")
    setup_database_fns(db)
    checkout = db.table("checkout")
    assert checkout.delete({"quantity": 50}, limit=2) == 2


def test_06_04_delete_order():
    """Test 0603 Delete limit with certain condition"""
    db = Database(":memory:")
    setup_database_fns(db)
    checkout = db.table("checkout")
    assert checkout.delete({"quantity": 50}, order="asc", limit=2) == 2  # type: ignore


def test_07_00_export_csv():
    """Test 0600 Export to CSV"""
    database = Database(":memory:")
    setup_database(database)
    csv = to_csv_string(database)
    print("test_07_00_export_csv\n", csv, "\n", file=pstdout, flush=True)
    assert csv


def test_07_01_export_file():
    """Test 0701 Export to CSV file"""
    database = Database(":memory:")
    setup_database(database)
    assert to_csv_file(database.table("users"), temp_dir / "users.csv")  # type: ignore


def test_07_02_export_directory():
    """Test 0702 Export to CSV as directory"""
    database = Database(":memory:")
    setup_database(database)
    assert to_csv_file(database, temp_dir / "MemDB")  # type: ignore


def test_08_00_function_count():
    """Test 0800 Count(*) usage"""
    database = Database(":memory:")
    setup_database_fns(database)
    counted = count("*")
    data = database.table("checkout").select(what=counted)
    print(data)
    assert data == 4


def test_09_00_select_error():
    """Test errors"""
    db = Database(":memory:")
    setup_database(db)
    groups = db.table("groups")
    with raises(OperationalError):
        groups.select({"nothing": None})


def test_10_01_pragma_foreign_key():
    """Test 1001 PRAGMA tests"""
    db = Database(":memory:")
    setup_database(db)
    db.foreign_pragma("ON")
    db.foreign_pragma("OFF")
    assert db.foreign_pragma() == {"foreign_keys": 0}


def test_10_02_pragma_optimize():
    """Test 1002 PRAGMA optimize"""
    db = Database(":memory:")
    setup_database(db)
    db.optimize()
    assert 1 == 1


def test_10_03_pragma_shrink():
    """Test 1003 PRAGMA shrink"""
    db = Database(":memory:")
    t = db.create_table("t", [integer("a")])
    t.insert_many([{"a": a} for a in range(10000)])
    t.commit()
    db.shrink_memory()
    assert 1 == 1


def test_10_04_vacuum():
    """Test 1004 vacuum"""
    db = Database(":memory:")
    t = db.create_table("t", [integer("a")])
    t.insert_many([{"a": a} for a in range(10000)])
    t.commit()
    _ = [t.delete_one({"a": randint(0, 1000)})]
    t.commit()
    db.vacuum()


def test_11_00_model_api():
    # pylint: disable=protected-access
    """Test 1100 Model API"""
    db = Database(":memory:")

    @model(db)
    class Users(BaseModel):  # type: ignore
        """Users"""

        __schema__ = (Primary("id"), Unique("username"))
        id: str
        username: str
        display_name: str
        is_active: bool = True

    assert db.table("users")._table == Users._tbl._table
    admin = Users.create(
        id=str(UUID(int=0)), username="admin", display_name="System Administrator"
    )
    assert admin.username
    fetched = Users.where(username="admin").fetch_one()
    assert fetched == admin


def test_11_01_model_relationship():
    """Test 1101 Model API Relationship"""

    db = Database(":memory:")

    Users, Posts = setup_model_api(db)

    admin = Users.create(id="0", username="Admin")
    post0 = Posts.create(
        id="0",
        title="Hello, World!",
        content="Lorem Ipsum Dolor sit Amet",
        user_id=admin.id,
    )
    user0 = Posts.belongs_to(post0, Users)
    assert admin == user0, "belongs_to() should return the correct user"
    assert post0 in admin.has_many(
        Posts
    ), "has_many() should return related posts to user"


def test_11_02_model_mixin():
    """Test 1102 Model API Mixins"""

    db = Database(":memory:")

    @model(db)
    class Posts(BaseModel, ScopeMixin, ChunkableMixin):
        """Posts"""

        __schema__ = (Primary("id"),)

        id: str
        title: str
        content: str
        is_active: bool

    Posts.bulk_create(
        [
            {"id": str(uuid4()), "title": "a", "content": "a", "is_active": True}
            for _ in range(10)
        ]
    )

    for posts in Posts.chunk_iter(5):
        assert all(map(lambda post: post.title, posts))

    assert Posts.active()


def test_11_03_model_hooks_and_validator():
    """Test 1103 Model API Hooks & Validators"""

    db = Database(":memory:")
    STATE = {"hooks": False, "validators": False}

    @model(db)
    class Users(BaseModel):
        """Base User class"""

        id: str
        username: str
        is_active: bool

    @Users.validator("is_active", "Active state is not True/False")
    def _(instance: Users):  # type: ignore
        STATE["validators"] = True
        return isinstance(instance.is_active, bool)

    @Users.hook("before_create")
    def _(instance: Users):
        STATE["hooks"] = True
        assert instance

    with raises(ValidationError):
        Users.create(id="0", username="admin", is_active=7773)
    Users.create(id="0", username="admin", is_active=True)

    assert STATE["hooks"]
    assert STATE["validators"]


def test_11_04_model_auto_id():
    """Test 1104 Model API Auto ID"""

    db = Database(":memory:")

    def auto_id():
        return str(uuid4())

    @model(db)
    class Users(BaseModel):
        """Base User class"""

        __schema__ = (Primary("id"),)
        __auto_id__ = auto_id
        id: str
        username: str
        is_active: bool

        # This also works!
        # @staticmethod
        # def __auto_id__():
        #     return str(uuid4())

    assert Users.create(username="admin", is_active=False).id

def test_11_05_model_hidden():
    """Test 1105 Model API __hidden__"""

    db = Database(":memory:")

    def auto_id():
        return str(uuid4())

    @model(db)
    class Users(BaseModel):
        """Base User class"""

        __schema__ = (Primary("id"),)
        __auto_id__ = auto_id
        __hidden__ = ("password",)
        id: str
        username: str
        password: str

    admin = Users.create(username="admin", password="admin123")
    admin_dict = admin.to_dict()
    assert "password" not in admin_dict
    assert admin.to_safe_instance().password is None

def test_11_06_model_fail():
    """Test 1105 Model API __hidden__"""

    db = Database(":memory:")

    def auto_id():
        return str(uuid4())

    @model(db)
    class Users(BaseModel):
        """Base User class"""

        __schema__ = (Primary("id"),)
        __auto_id__ = auto_id
        __hidden__ = ("password",)
        id: str
        username: str
        password: str

    Users.first()
    with raises(NoDataReturnedError):
        Users.find_or_fail(1)

def test_98_00_test():
    """Gradual test"""
    db = Database(":memory:")
    setup_orderable(db)
    items = db.table("items")
    v0 = items.select({"quantity": this == 99})
    STATE["DEBUG"] = True
    values = items.select({"quantity": in_([99, 98, 97])})
    assert v0
    assert values
    STATE["DEBUG"] = False


def test_99_99_save_report():
    """FINAL 9999 Save reports"""
    with open(file, "w", encoding="utf-8") as xfile:
        xfile.write(pstdout.getvalue())


def test_100_pity():
    """FINAL"""
    # 99% success rate
    assert random() < 0.99
