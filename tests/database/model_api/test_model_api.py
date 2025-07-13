"""Model API tests"""

from uuid import UUID, uuid4
from pytest import raises
from sqlite_database import Database, model, Primary, Unique, BaseModel
from sqlite_database.models.mixin import ScopeMixin, ChunkableMixin
from sqlite_database.models.errors import ValidationError, NoDataReturnedError

from ..setup import setup_model_api

def test_model_api():
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


def test_model_relationship():
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


def test_model_mixin():
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

def test_model_hooks_usability():
    """Test Model API if hooks can be used"""

    db = Database(":memory:")
    called = {"before_create": False}

    @model(db)
    class Users(BaseModel):
        """Base User class"""

        id: str
        username: str
        is_active: bool

    @Users.hook("before_create")
    def before_create_hook(_: Users):
        called["before_create"] = True

    Users.create(id="2", username="admin", is_active=True)

    assert called['before_create'] is True, "Hooks is not called"

def test_model_hooks_and_validator():
    """Test Model API Validators"""

    db = Database(":memory:")

    @model(db)
    class Users(BaseModel):
        """Base User class"""

        id: str
        username: str
        is_active: bool

    @Users.validator("is_active", "Active state is not True/False")
    def _(instance: Users):  # type: ignore
        return isinstance(instance.is_active, bool)

    with raises(ValidationError):
        Users.create(id="0", username="admin", is_active=7773)
    Users.create(id="0", username="admin", is_active=True)

def test_model_auto_id():
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

def test_model_hidden():
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

def test_model_fail():
    """Test 1106 Model API fail-able methods"""

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

    assert Users.first() is None, "Users class has unexpected data"
    with raises(NoDataReturnedError):
        Users.find_or_fail(1)

def test_model_api_runtime_typechecking():
    """Test Model API runtime type checking"""

    db = Database(":memory:")

    def auto_id():
        return str(uuid4())

    @model(db, True)
    class Users(BaseModel):
        """Base User class"""

        __schema__ = (Primary("id"),)
        __auto_id__ = auto_id
        __hidden__ = ("password",)
        id: str
        username: str
        password: str

    with raises(ValidationError):
        Users.create(id=0, username=0, password=0)

    assert Users.first() is None, "How?"
