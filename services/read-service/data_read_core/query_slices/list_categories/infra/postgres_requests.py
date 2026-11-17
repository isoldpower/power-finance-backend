from django.db.models import Q, QuerySet

from data_read_core.shared.pagination import PageRequest, apply_keyset
from data_read_core.shared.postgres_orm import CategoryReadModel


def _visible_queryset(user_id: int, kind: str | None) -> QuerySet[CategoryReadModel]:
    queryset = CategoryReadModel.objects.filter(
        Q(is_global=True) | Q(user_id=user_id),
        deleted_at__isnull=True,
    )
    if kind is not None:
        queryset = queryset.filter(kind=kind)

    return queryset


async def fetch_visible_categories(
    user_id: int,
    kind: str | None,
    page: PageRequest,
) -> list[CategoryReadModel]:
    queryset = apply_keyset(_visible_queryset(user_id, kind), page)

    return [category async for category in queryset]


async def count_visible_categories(user_id: int, kind: str | None) -> int:
    return await _visible_queryset(user_id, kind).acount()
