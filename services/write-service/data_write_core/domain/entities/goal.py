from datetime import datetime
from decimal import Decimal

from ..events import EventCollector
from ..value_objects import GoalData
from ._entity_root import EntityRoot

UNCHANGED = object()


class GoalEntity(EntityRoot, GoalData):
    _user_id: str
    _created_at: datetime
    _updated_at: datetime | None
    _deleted_at: datetime | None

    def __init__(
        self,
        id: str,
        title: str,
        currency_code: str,
        target: Decimal,
        created_at: datetime,
        user_id: str,
        event_collector: EventCollector,
        finish_at: datetime | None = None,
        url: str | None = None,
        updated_at: datetime | None = None,
        deleted_at: datetime | None = None,
    ) -> None:
        EntityRoot.__init__(self=self, unique_id=id, collector=event_collector)
        GoalData.__init__(
            self=self,
            title=title,
            currency_code=currency_code,
            target=target,
            finish_at=finish_at,
            url=url,
        )

        self._user_id = user_id
        self._created_at = created_at
        self._updated_at = updated_at
        self._deleted_at = deleted_at

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime | None:
        return self._updated_at

    @property
    def deleted_at(self) -> datetime | None:
        return self._deleted_at

    def mark_deleted(self, now: datetime) -> None:
        self._deleted_at = now
        self._updated_at = now

    def restore(self, now: datetime) -> None:
        self._deleted_at = None
        self._updated_at = now

    def snapshot(self) -> GoalData:
        return GoalData(
            title=self.title,
            currency_code=self.currency_code,
            target=self.target,
            finish_at=self.finish_at,
            url=self.url,
        )

    def apply(self, data: GoalData, now: datetime) -> None:
        """Restore a previous snapshot. `currency_code` is deliberately not restored:
        it never changed, so writing it back would be the only path by which a bug
        here could move it."""
        self.title = data.title
        self.target = data.target
        self.finish_at = data.finish_at
        self.url = data.url
        self._updated_at = now

    def update_metadata(
        self,
        now: datetime,
        title: str | object = UNCHANGED,
        target: Decimal | object = UNCHANGED,
        finish_at: datetime | None | object = UNCHANGED,
        url: str | None | object = UNCHANGED,
    ) -> bool:
        changed = False
        for name, value in (
            ("title", title),
            ("target", target),
            ("finish_at", finish_at),
            ("url", url),
        ):
            if value is UNCHANGED or getattr(self, name) == value:
                continue

            setattr(self, name, value)
            changed = True

        if changed:
            self._updated_at = now

        return changed

    @classmethod
    def create(
        cls,
        data: GoalData,
        id: str,
        user_id: str,
        created_at: datetime,
        updated_at: datetime | None = None,
        deleted_at: datetime | None = None,
        _event_collector: EventCollector | None = None,
    ) -> "GoalEntity":
        return cls(
            id=id,
            title=data.title,
            currency_code=data.currency_code,
            target=data.target,
            finish_at=data.finish_at,
            url=data.url,
            user_id=user_id,
            created_at=created_at,
            updated_at=updated_at,
            deleted_at=deleted_at,
            event_collector=_event_collector or EventCollector(),
        )
