"""Mixin Helpers"""

# pylint: disable=too-few-public-methods

from typing import TypeVar, Callable, Type, Generator
from . import BaseModel

BaseModelT = TypeVar("BaseModelT", bound=BaseModel)


class BaseModelMixin:
    """Base class for all Mixins"""


class ScopeMixin(BaseModelMixin):
    """Scope-related mixins"""

    @classmethod # type: ignore
    def active(cls: Type[BaseModelT]) -> list[BaseModelT]:  # type: ignore
        """Return any active users"""
        return cls.where(is_active=True).fetch()


class ChunkableMixin(BaseModelMixin):
    """Implement chunk related stuff"""

    @classmethod  # type: ignore
    def chunk(
        cls: Type[BaseModelT],  # type: ignore
        limit: int,
        callback: Callable[[list[BaseModelT]], None],
    ):
        """Return specified instance by the amount of limit, or execute provided callback"""
        offset = 0
        while True:
            batch = cls.query().limit(limit).offset(offset).fetch()

            if not batch:
                break

            callback(batch)

            if len(batch) != limit:
                break

            offset += limit

    @classmethod  # type: ignore
    def chunk_iter(cls: Type[BaseModelT], # type: ignore
                   limit: int) -> Generator[list[BaseModelT], None, None]:  # type: ignore
        """Yield specifiec range instanced by the amount of limit."""
        offset = 0
        while True:
            batch = cls.query().limit(limit).offset(offset).fetch()

            if not batch:
                break

            yield batch

            if len(batch) != limit:
                break

            offset += limit
