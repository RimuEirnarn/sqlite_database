"""Model QueryBuilder"""

from __future__ import annotations
from typing import Type
from ..column import check_one
from . import models


class QueryBuilder:
    """Query builder for Model ORM"""

    def __init__(self, model: Type[models.ModelProtocol]) -> None:
        self._model = model
        self._filters = {}
        self._limit = 0
        self._offset = 0
        self._order = None

    def where(self, **kwargs):
        """Sets conditioning"""
        self._filters.update(kwargs)
        return self

    def limit(self, value: int):
        """Sets limit"""
        self._limit = value
        return self

    def offset(self, value: int):
        """Sets offset"""
        self._offset = value
        return self

    def order_by(self, column: str, descending: bool = False):
        """Order the query by a column"""
        self._order = (check_one(column), "asc" if descending is False else "desc")
        return self

    def fetch(self) -> list[models.ModelProtocol]:
        """Fetch data from table"""
        return [
            self._model(**record)
            for record in self._model._tbl.select( # pylint: disable=protected-access
                self._filters, limit=self._limit, offset=self._offset, order=self._order
            )
        ]
