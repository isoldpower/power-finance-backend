from datetime import datetime

from kafka_messages import AccountUpdated

from ....shared.kafka_outbox import OutboxEntry, build_outbox_entry
from ..contracts import BalanceChange
from ._account_groups import account_group_of
from ._aggregates import ACCOUNT_AGGREGATE
from ._money import money


def account_updated(
    change: BalanceChange,
    *,
    user_id: int,
    user_external_id: str,
    updated_at: datetime,
) -> OutboxEntry:
    message = AccountUpdated(
        account_id=str(change.account_id),
        user_external_id=user_external_id,
        user_id=user_id,
        previous_balance=money(change.previous),
        new_balance=money(change.current),
        account_group=account_group_of(change.group),
        name=change.name,
        currency_code=change.currency_code,
    )
    message.updated_at.FromDatetime(updated_at)

    return build_outbox_entry(
        message,
        aggregate_type=ACCOUNT_AGGREGATE,
        aggregate_id=str(change.account_id),
        partition_key=user_external_id,
    )
