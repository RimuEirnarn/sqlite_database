"""MySQL wrapper"""

# The reason it's here is because github doesn't support forking of the same owner
# Oh well, anyway.

from typing import Any
from urllib.parse import urlsplit, parse_qs
from random import randint

try:
    import mysql.connector # type: ignore
except ModuleNotFoundError:
    from ..errors import DependencyError
    raise DependencyError("mysql-connector is not found, reinstall with sqlite-database[mysql]")\
        from None

from ..database import Database

class MySQLDatabase(Database):
    """MySQL database"""

    def __new__(cls, config: dict[str, Any], **kwargs):
        rid = randint(0, 10000)
        return super().__new__(cls, f"--::MYSQL-{rid}::--", **kwargs)

    def __init__(self, config: dict[str, Any], **kwargs) -> None:
        super().__init__("--mysql", **kwargs)

        self._database = mysql.connector.connect(**config)

    @classmethod
    def connect_from_uri(cls, uri: str, **kwargs):
        """Connect from a URI.

        Example of correct URI would be:
        mysql://user:password@hostname:3306/database_name

        Any queries can be used as mysql connector.connect keyword arguments"""
        config: dict[str, Any] = {}
        uri_data = urlsplit(uri)
        if uri_data.scheme != "mysql":
            raise ValueError(f"Expected scheme mysql, got {uri_data.scheme}")
        config['user'] = uri_data.username
        config['password'] = uri_data.password
        config['host'] = uri_data.hostname
        config['port'] = uri_data.port or 3306
        config['database'] = uri_data.path.split('/')[1]
        for key, value in parse_qs(uri_data.query):
            if key not in config:
                config[key] = value[0]
        return cls(config, **kwargs)
