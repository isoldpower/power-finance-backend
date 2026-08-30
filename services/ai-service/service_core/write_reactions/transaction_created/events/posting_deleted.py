from datetime import datetime
from uuid import UUID

from kafka_messages import AccountPostingDeleted

from ....shared.kafka_outbox import OutboxEntry, build_outbox_entry
from ..contracts import RemovedPosting
from ._aggregates import POSTING_AGGREGATE


def posting_deleted(
    posting: RemovedPosting,
    *,
    dispatch_id: UUID,
    transaction_id: UUID,
    user_id: int,
    user_external_id: str,
    deleted_at: datetime,
) -> OutboxEntry:
    message = AccountPostingDeleted(
        posting_id=str(posting.posting_id),
        dispatch_id=str(dispatch_id),
        account_id=str(posting.account_id),
        transaction_id=str(transaction_id),
        user_external_id=user_external_id,
        user_id=user_id,
    )
    message.deleted_at.FromDatetime(deleted_at)

    return build_outbox_entry(
        message,
        aggregate_type=POSTING_AGGREGATE,
        aggregate_id=str(transaction_id),
        partition_key=user_external_id,
    )
