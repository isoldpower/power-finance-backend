from datetime import datetime
from uuid import UUID

from kafka_messages import AccountPostingsDispatched

from ....shared.kafka_outbox import OutboxEntry, build_outbox_entry
from ._aggregates import POSTING_AGGREGATE


def postings_dispatched(
    *,
    dispatch_id: UUID,
    transaction_id: UUID,
    user_id: int,
    user_external_id: str,
    deleted_count: int,
    created_count: int,
    balanced: bool,
    comment: str,
    backend: str,
    dispatched_at: datetime,
) -> OutboxEntry:
    message = AccountPostingsDispatched(
        dispatch_id=str(dispatch_id),
        transaction_id=str(transaction_id),
        user_external_id=user_external_id,
        user_id=user_id,
        deleted_count=deleted_count,
        created_count=created_count,
        balanced=balanced,
        comment=comment,
        backend=backend,
    )
    message.dispatched_at.FromDatetime(dispatched_at)

    return build_outbox_entry(
        message,
        aggregate_type=POSTING_AGGREGATE,
        aggregate_id=str(transaction_id),
        partition_key=user_external_id,
    )
