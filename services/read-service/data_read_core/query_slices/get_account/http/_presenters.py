from data_read_core.shared.money import money_at_scale
from data_read_core.shared.pagination import Page

from ..dtos import AccountDetailDTO, HistoryEntryDTO


async def present_history_entry(entry: HistoryEntryDTO) -> dict:
    return {
        "id": entry.id,
        "title": entry.title,
        "debit": entry.debit,
        "created_at": entry.created_at,
        "source_transaction": entry.source_transaction,
        "icon": entry.icon,
        "money": await money_at_scale(
            entry.amount,
            entry.currency,
        ),
    }


def present_history_meta(
    namespace: str,
    page: Page,
    cached: bool,
) -> dict:
    return {
        **page.meta(namespace=namespace),
        "cached": cached,
    }


async def present_one(
    detail: AccountDetailDTO,
    history: list[HistoryEntryDTO],
) -> dict:
    account = detail.account

    return {
        "id": account.id,
        "group": account.group,
        "name": account.name,
        "created_at": account.created_at,
        "updated_at": account.updated_at,
        "money": await money_at_scale(
            account.balance_amount,
            account.currency,
        ),
        "history": [await present_history_entry(entry) for entry in history],
    }
