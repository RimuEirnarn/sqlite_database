"""Errors"""


class SecurityError(Exception):
    """SQLInjection ahead."""


class UnexpectedResultError(Exception):
    """Result of something is unexpected."""


class TableRemovedError(Exception):
    """Table is removed"""


class DatabaseExistsError(UnexpectedResultError):
    """Database that would be created is already exists."""


class DatabaseMissingError(UnexpectedResultError):
    """Database that would be accessed is missing."""
