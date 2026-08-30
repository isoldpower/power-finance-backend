from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from service_core.shared.kafka_outbox import OutboxEntry

from ..contracts import BalanceChange, RemovedPosting
from .account_updated import account_updated
from .posting_deleted import posting_deleted
from .postings_dispatched import postings_dispatched


def removal_events(
    *,
    removed: Sequence[RemovedPosting],
    changes: Sequence[BalanceChange],
    dispatch_id: UUID,
    transaction_id: UUID,
    user_id: int,
    user_external_id: str,
    now: datetime,
) -> list[OutboxEntry]:
    """The events one deletion produces, in the order consumers see them."""

    entries_list = [
        posting_deleted(
            posting,
            dispatch_id=dispatch_id,
            transaction_id=transaction_id,
            user_id=user_id,
            user_external_id=user_external_id,
            deleted_at=now,
        )
        for posting in removed
    ]
    entries_list.append(
        postings_dispatched(
            dispatch_id=dispatch_id,
            transaction_id=transaction_id,
            user_id=user_id,
            user_external_id=user_external_id,
            deleted_count=len(removed),
            created_count=0,
            balanced=True,
            comment="",
            backend="",
            dispatched_at=now,
        )
    )
    entries_list += [
        account_updated(
            change,
            user_id=user_id,
            user_external_id=user_external_id,
            updated_at=now,
        )
        for change in changes
    ]

    return entries_list
