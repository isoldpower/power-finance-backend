from decimal import Decimal

from kafka_messages import AccountGroup

from data_read_core.shared.money import DEFAULT_CURRENCY
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


def book_currency_of(raw_currency: str) -> str:
    return raw_currency or DEFAULT_CURRENCY
