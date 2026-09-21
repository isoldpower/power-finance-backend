from datetime import datetime
from decimal import Decimal

from ..events import EventCollector
from ..value_objects import WalletData
from ._entity_root import EntityRoot

UNCHANGED = object()


class WalletEntity(EntityRoot, WalletData):
    _user_id: str
    _created_at: datetime
    _updated_at: datetime
    _deleted_at: datetime | None

    def __init__(
        self,
        id: str,
        title: str,
        currency_code: str,
        created_at: datetime,
        updated_at: datetime,
        user_id: str,
        event_collector: EventCollector,
        deleted_at: datetime | None = None,
        category: str = "",
        color: str = "",
        favorite: bool = False,
        zero_balance: Decimal = Decimal("0"),
    ):
        EntityRoot.__init__(self=self, unique_id=id, collector=event_collector)
        WalletData.__init__(
            self=self,
            title=title,
            currency_code=currency_code,
            category=category,
            color=color,
            favorite=favorite,
            zero_balance=zero_balance,
        )

        self._created_at = created_at
        self._updated_at = updated_at
        self._deleted_at = deleted_at
        self._user_id = user_id

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
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

    def rename(self, new_title: str, now: datetime) -> None:
        self.title = new_title
        self._updated_at = now

    def snapshot(self) -> WalletData:
        return WalletData(
            title=self.title,
            currency_code=self.currency_code,
            category=self.category,
            color=self.color,
            favorite=self.favorite,
            zero_balance=self.zero_balance,
        )

    def apply(self, data: WalletData, now: datetime) -> None:
        self.title = data.title
        self.category = data.category
        self.color = data.color
        self.favorite = data.favorite
        self.zero_balance = data.zero_balance
        self._updated_at = now

    def update_metadata(
        self,
        now: datetime,
        title: str | object = UNCHANGED,
        category: str | object = UNCHANGED,
        color: str | object = UNCHANGED,
        favorite: bool | object = UNCHANGED,
        zero_balance: Decimal | object = UNCHANGED,
    ) -> bool:
        changed = False
        for name, value in (
            ("title", title),
            ("category", category),
            ("color", color),
            ("favorite", favorite),
            ("zero_balance", zero_balance),
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
        data: WalletData,
        id: str,
        user_id: str,
        created_at: datetime,
        updated_at: datetime,
        deleted_at: datetime | None = None,
        _event_collector: EventCollector | None = None,
    ):
        return cls(
            id=id,
            title=data.title,
            currency_code=data.currency_code,
            category=data.category,
            color=data.color,
            favorite=data.favorite,
            zero_balance=data.zero_balance,
            user_id=user_id,
            created_at=created_at,
            updated_at=updated_at,
            deleted_at=deleted_at,
            event_collector=_event_collector or EventCollector(),
        )
