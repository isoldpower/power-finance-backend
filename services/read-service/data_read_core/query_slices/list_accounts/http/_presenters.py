from ..dtos import AccountDTO


async def present_one(account: AccountDTO) -> dict:
    return {
        "id": account.id,
        "group": account.group,
        "name": account.name,
        "balance": account.balance_amount,
        "created_at": account.created_at,
        "updated_at": account.updated_at,
    }


async def present_many(accounts: list[AccountDTO]) -> list[dict]:
    return [await present_one(account) for account in accounts]
