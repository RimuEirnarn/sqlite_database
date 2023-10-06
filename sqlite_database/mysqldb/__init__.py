"""MySQL wrapper"""

# The reason it's here is because github doesn't support forking of the same owner
# Oh well, anyway.

from typing import Any

try:
    import mysql.connector # type: ignore
except ModuleNotFoundError:
    from ..errors import DependencyError
    raise DependencyError("mysql-connector is not found, reinstall with sqlite-database[mysql]")\
        from None

from ..database import Database

class MySQLDatabase(Database):
    """MySQL database"""

    def __init__(self, config: dict[str, Any], **kwargs) -> None:
        mysql.connector.connect(config)
        super().__init__("--mysql", **kwargs)
