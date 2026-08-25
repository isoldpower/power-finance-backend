from data_read_core.shared.money import money_at_scale
from data_read_core.shared.pagination import Page

from ..dtos import GoalDetailDTO, HistoryEntryDTO


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
    detail: GoalDetailDTO,
    history: list[HistoryEntryDTO],
) -> dict:
    goal = detail.goal

    return {
        "id": goal.id,
        "name": goal.name,
        "url": goal.url,
        "currency": goal.currency,
        "finish_at": goal.finish_at,
        "created_at": goal.created_at,
        "updated_at": goal.updated_at,
        "deleted_at": goal.deleted_at,
        "target": await money_at_scale(
            goal.target_amount,
            goal.currency,
        ),
        "progress": await money_at_scale(
            goal.progress_amount,
            goal.currency,
        ),
        "history": [await present_history_entry(entry) for entry in history],
    }
