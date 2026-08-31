from decimal import Decimal

from data_read_core.shared.money import money_at_scale

from ..dtos import AccountPostingDTO


async def present_one(posting: AccountPostingDTO) -> dict:
    return {
        "id": posting.id,
        "account_id": posting.account_id,
        "transaction_id": posting.transaction_id,
        "title": posting.title,
        "icon": posting.icon,
        "debit": posting.debit,
        "position": posting.position,
        "money": await money_at_scale(Decimal(posting.amount), posting.currency),
        "created_at": posting.created_at,
    }


async def present_many(postings: list[AccountPostingDTO]) -> list[dict]:
    return [await present_one(posting) for posting in postings]
