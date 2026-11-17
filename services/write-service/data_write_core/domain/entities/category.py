from datetime import datetime
from uuid import UUID

from ..events import EventCollector
from ..value_objects import CategoryKind, CategoryReference
from ._entity_root import EntityRoot


class CategoryEntity(EntityRoot):
    def __init__(
        self,
        id: UUID,
        kind: CategoryKind,
        name: str,
        user_id: str | None,
        is_global: bool,
        created_at: datetime,
        event_collector: EventCollector,
        updated_at: datetime | None = None,
        deleted_at: datetime | None = None,
    ) -> None:
        EntityRoot.__init__(self, unique_id=str(id), collector=event_collector)
        self.kind = kind
        self.name = name
        self._user_id = user_id
        self._is_global = is_global
        self._created_at = created_at
        self._updated_at = updated_at
        self._deleted_at = deleted_at

    @property
    def user_id(self) -> str | None:
        return self._user_id

    @property
    def is_global(self) -> bool:
        return self._is_global

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime | None:
        return self._updated_at

    @property
    def deleted_at(self) -> datetime | None:
        return self._deleted_at

    def rename(self, new_name: str, now: datetime) -> bool:
        if self.name == new_name:
            return False

        self.name = new_name
        self._updated_at = now
        return True

    def mark_deleted(self, now: datetime) -> None:
        self._deleted_at = now
        self._updated_at = now

    def restore(self, now: datetime) -> None:
        self._deleted_at = None
        self._updated_at = now

    def as_reference(self) -> CategoryReference:
        return CategoryReference(id=UUID(self.unique_id), name=self.name, is_global=self.is_global)

    @classmethod
    def create_owned(
        cls,
        id: UUID,
        kind: CategoryKind,
        name: str,
        user_id: str,
        created_at: datetime,
    ) -> "CategoryEntity":
        return cls(
            id=id,
            kind=kind,
            name=name,
            user_id=user_id,
            is_global=False,
            created_at=created_at,
            event_collector=EventCollector(),
        )
