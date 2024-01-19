"""Database"""

from .database import Database
from ._utils import null, AttrDict
from .column import Column, text, integer, blob, real
from .signature import op
from .table import Table

def test_installed():
    """Is the module installed?"""
    return True

__version__ = "0.4.4"
__all__ = ["Database", "Table", "op",
           "Column", "null", 'AttrDict', 'text', 'integer', 'real', 'blob']
