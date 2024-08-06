"""Database"""

from .database import Database
from ._utils import null, Row
from .column import Column, text, integer, blob, real
from .signature import op
from .operators import this
from .table import Table


def test_installed():
    """Is the module installed?"""
    return True


__version__ = "0.5.0"
__all__ = [
    "Database",
    "Table",
    "this",
    "op",
    "Column",
    "null",
    "Row",
    "text",
    "integer",
    "real",
    "blob",
]
