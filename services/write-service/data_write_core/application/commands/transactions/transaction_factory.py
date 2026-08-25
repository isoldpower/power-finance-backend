from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from data_write_core.domain.aggregates import TransactionAggregate
from data_write_core.domain.entities import MoneyFlowEntity, TransactionEntity
from data_write_core.domain.events import TransactionCreatedEvent
from data_write_core.domain.exceptions import InvalidTransactionAmountError
from data_write_core.domain.value_objects import (
    MoneyContainerRef,
    MoneyFlowData,
    TransactionMetadata,
    TransactionType,
)


def build_transaction(
    user_id: int,
    container: MoneyContainerRef,
    metadata: TransactionMetadata,
    amount: Decimal,
    transaction_type: TransactionType,
    created_at: datetime,
) -> TransactionAggregate:
    """Assemble a transaction and its opening flow."""
    if amount == Decimal("0"):
        raise InvalidTransactionAmountError(amount)

    transaction_id = uuid4()
    transaction = TransactionEntity.create(
        id=transaction_id,
        user_id=user_id,
        container_id=container.id,
        container_kind=container.kind,
        metadata=metadata,
        created_at=created_at,
    )
    signed_amount = TransactionEntity.signed(amount, transaction_type)
    opening_flow = MoneyFlowEntity.create(
        user_id=user_id,
        created_at=created_at,
        data=MoneyFlowData(
            transaction_id=transaction_id,
            container_id=container.id,
            amount=signed_amount,
        ),
        _event_collector=transaction.event_collector,
    )
    transaction.events_occurred(
        TransactionCreatedEvent(
            transaction_id=transaction_id,
            container_id=container.id,
            container_kind=container.kind,
            user_id=user_id,
            amount=signed_amount,
            created_at=created_at,
        )
    )

    return TransactionAggregate(
        transaction_entity=transaction,
        flows=[opening_flow],
    )
