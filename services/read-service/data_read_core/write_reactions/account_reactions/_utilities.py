from decimal import Decimal

from kafka_messages import AccountGroup

from data_read_core.shared.postgres_orm import AccountGroups

_GROUP_NAMES: dict[int, str] = {
    AccountGroup.ACCOUNT_GROUP_ASSETS: AccountGroups.ASSETS,
    AccountGroup.ACCOUNT_GROUP_LIABILITIES: AccountGroups.LIABILITIES,
    AccountGroup.ACCOUNT_GROUP_EQUITY: AccountGroups.EQUITY,
}


def group_name_of(account_group: int) -> str:
    return _GROUP_NAMES.get(account_group, "")


def money_of(raw: str) -> Decimal:
    return Decimal(raw or "0")
