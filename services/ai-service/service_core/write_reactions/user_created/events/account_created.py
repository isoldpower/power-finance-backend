from kafka_messages import AccountCreated

from service_core.shared.kafka_outbox import (
    OutboxEntry,
    build_outbox_entry,
)

from ..contracts import AccountRecord
from ._account_groups import account_group_of
from ._aggregates import ACCOUNT_AGGREGATE
from ._money import money


def account_created(
    account: AccountRecord,
    *,
    user_id: int,
    user_external_id: str,
) -> OutboxEntry:
    message = AccountCreated(
        account_id=str(account.account_id),
        user_external_id=user_external_id,
        user_id=user_id,
        account_group=account_group_of(account.group),
        name=account.name,
        balance=money(account.balance),
        currency_code=account.currency_code,
    )
    message.created_at.FromDatetime(account.created_at)

    return build_outbox_entry(
        message,
        aggregate_type=ACCOUNT_AGGREGATE,
        aggregate_id=str(account.account_id),
        partition_key=user_external_id,
    )
