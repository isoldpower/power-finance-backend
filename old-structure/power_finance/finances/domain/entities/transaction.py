import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from django.utils import timezone

from finances.domain.events import EventCollector, TransactionCreatedEvent, TransactionDeletedEvent


@dataclass
class Transaction:
    id: UUID
    user_id: int
    source_wallet_id: UUID
    amount: Decimal
    created_at: datetime
    cancels_other: UUID | None = None
    adjusts_other: UUID | None = None
    _event_collector: EventCollector = field(default_factory=EventCollector, compare=False)

    @classmethod
    def create(
            cls,
            user_id: int,
            source_wallet_id: UUID,
            amount: Decimal,
            cancels_other: UUID | None = None,
            adjusts_other: UUID | None = None,
            event_collector: EventCollector | None = None,
    ):
        created_transaction = cls(
            id=uuid.uuid4(),
            user_id=user_id,
            source_wallet_id=source_wallet_id,
            amount=amount,
            created_at=datetime.now(),
            cancels_other=cancels_other,
            adjusts_other=adjusts_other,
            _event_collector=event_collector or EventCollector(),
        )

        created_transaction._event_collector.collect(TransactionCreatedEvent(
            transaction_id=created_transaction.id,
            wallet_id=source_wallet_id,
            created_at=created_transaction.created_at,
            user_id=created_transaction.user_id,
            amount=created_transaction.amount,
        ))

        return created_transaction

    @classmethod
    def from_persistence(
            cls,
            transaction_id: UUID,
            user_id: int,
            wallet_id: UUID,
            amount: Decimal,
            created_at: datetime,
            cancels_other: UUID | None = None,
            adjusts_other: UUID | None = None,
            event_collector: EventCollector | None = None,
    ):
        return cls(
            id=transaction_id,
            user_id=user_id,
            source_wallet_id=wallet_id,
            amount=amount,
            created_at=created_at,
            cancels_other=cancels_other,
            adjusts_other=adjusts_other,
            _event_collector=event_collector or EventCollector(),
        )

    def migrate_event_collector(
            self,
            event_collector: EventCollector
    ):
        recorded_events = self._event_collector.pull_events()
        for event in recorded_events:
            event_collector.collect(event)

        self._event_collector = event_collector

    def get_inverse(self):
        return Transaction.create(
            user_id=self.user_id,
            source_wallet_id=self.source_wallet_id,
            amount=self.amount * -1,
            cancels_other=self.id,
        )

    def delete(self) -> 'Transaction':
        inverse = self.get_inverse()
        inverse._event_collector.collect(TransactionDeletedEvent(
            transaction_id=self.id,
            wallet_id=self.source_wallet_id,
            user_id=self.user_id,
            amount=self.amount,
            cancelled_by=inverse.id,
            created_at=inverse.created_at,
        ))
        return inverse
