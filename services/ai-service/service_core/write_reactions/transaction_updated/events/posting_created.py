from datetime import datetime
from uuid import UUID

from kafka_messages import AccountPostingCreated

from service_core.shared.kafka_outbox import (
    OutboxEntry,
    build_outbox_entry,
)

from ..contracts import StoredPosting
from ._aggregates import POSTING_AGGREGATE
from ._money import money


def posting_created(
    posting: StoredPosting,
    *,
    dispatch_id: UUID,
    transaction_id: UUID,
    user_id: int,
    user_external_id: str,
    created_at: datetime,
) -> OutboxEntry:
    leg = posting.leg
    message = AccountPostingCreated(
        posting_id=str(posting.posting_id),
        dispatch_id=str(dispatch_id),
        account_id=str(leg.account_id),
        transaction_id=str(transaction_id),
        user_external_id=user_external_id,
        user_id=user_id,
        amount=money(leg.amount),
        title=leg.title,
        icon=leg.icon,
        debit=leg.debit,
        currency_code=leg.currency_code or "",
        position=leg.position,
    )
    message.created_at.FromDatetime(created_at)

    return build_outbox_entry(
        message,
        aggregate_type=POSTING_AGGREGATE,
        aggregate_id=str(transaction_id),
        partition_key=user_external_id,
    )
