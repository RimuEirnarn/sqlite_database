"""Errors"""


class SecurityError(Exception):
    """SQLInjection ahead."""


class UnexpectedResultError(Exception):
    """Result of something is unexpected."""


class TableRemovedError(Exception):
    """Table is removed"""
