from kafka_messages import AccountGroup

_ACCOUNT_GROUPS: dict[str, AccountGroup.ValueType] = {
    "assets": AccountGroup.ACCOUNT_GROUP_ASSETS,
    "liabilities": AccountGroup.ACCOUNT_GROUP_LIABILITIES,
    "equity": AccountGroup.ACCOUNT_GROUP_EQUITY,
}


def account_group_of(group: str) -> AccountGroup.ValueType:
    """The proto spelling of a stored group name."""

    return _ACCOUNT_GROUPS.get(
        group.lower(),
        AccountGroup.ACCOUNT_GROUP_WRONG,
    )
