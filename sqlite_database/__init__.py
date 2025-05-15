"""Database"""

from .models import BaseModel, model, Foreign, Primary, Unique
from .database import Database
from ._utils import null, Row, Null
from .column import Column, text, integer, blob, real
from .signature import op
from .operators import this
from .table import Table


def test_installed():
    """Is the module installed?"""
    return True


__version__ = "0.7.3"
__all__ = [
    "Database",
    "Table",
    "this",
    "op",
    "Column",
    "null",
    "Null",
    "Row",
    "text",
    "integer",
    "real",
    "blob",
    "BaseModel",
    "models",
    "Foreign",
    "Primary",
    "Unique"
]
