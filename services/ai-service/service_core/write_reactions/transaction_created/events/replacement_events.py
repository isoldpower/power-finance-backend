from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from service_core.shared.kafka_outbox import OutboxEntry

from ..contracts import BalanceChange, RemovedPosting, StoredPosting
from .account_updated import account_updated
from .posting_created import posting_created
from .posting_deleted import posting_deleted
from .postings_dispatched import postings_dispatched


def replacement_events(
    *,
    removed: Sequence[RemovedPosting],
    created: Sequence[StoredPosting],
    changes: Sequence[BalanceChange],
    dispatch_id: UUID,
    transaction_id: UUID,
    user_id: int,
    user_external_id: str,
    balanced: bool,
    comment: str,
    backend: str,
    now: datetime,
) -> list[OutboxEntry]:
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
    entries_list += [
        posting_created(
            posting,
            dispatch_id=dispatch_id,
            transaction_id=transaction_id,
            user_id=user_id,
            user_external_id=user_external_id,
            created_at=now,
        )
        for posting in created
    ]
    entries_list.append(
        postings_dispatched(
            dispatch_id=dispatch_id,
            transaction_id=transaction_id,
            user_id=user_id,
            user_external_id=user_external_id,
            deleted_count=len(removed),
            created_count=len(created),
            balanced=balanced,
            comment=comment,
            backend=backend,
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
