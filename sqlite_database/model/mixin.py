"""Mixin Helpers"""

# pylint: disable=too-few-public-methods

from typing import TypeVar, Callable
from . import BaseModel

BaseModelT = TypeVar("BaseModelT", bound=BaseModel)

class BaseModelMixin:
    """Base class for all Mixins"""


class ScopeMixin(BaseModelMixin):
    """Scope-related mixins"""

    def active(self: BaseModelT):  # type: ignore
        """Return any active users"""
        return self.where(is_active=True).fetch()


class ChunkableMixin(BaseModelMixin):
    """Implement chunk related stuff"""

    def chunk(self: BaseModelT, # type: ignore
              limit: int,
              callback: Callable[[list[BaseModelT]], None]):
        """Return specified instance by the amount of limit, or execute provided callback"""
        offset = 0
        while True:
            batch = self.query().limit(limit).offset(offset).fetch()

            if not batch:
                break

            callback(batch)

            if len(batch) != limit:
                break

            offset += limit

    def chunk_iter(self: BaseModelT, limit: int): # type: ignore
        """Yield specifiec range instanced by the amount of limit."""
        offset = 0
        while True:
            batch = self.query.limit(limit).offset(offset).fetch()

            if not batch:
                break

            yield batch

            if len(batch) != limit:
                break

            offset += limit
