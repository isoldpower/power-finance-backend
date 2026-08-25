from uuid import UUID

from data_write_core.application.interfaces import MoneyContainerRepository
from data_write_core.domain.exceptions import MoneyContainerNotFoundError
from data_write_core.domain.value_objects import MoneyContainerKind, MoneyContainerRef

from ..orm import MoneyContainerModel

_REFERENCE_FIELDS = ("id", "kind", "name", "currency_id", "deleted_at")


class DjangoMoneyContainerRepository(MoneyContainerRepository):
    async def resolve(self, container_id: UUID, user_id: int) -> MoneyContainerRef:
        container_row = await (
            MoneyContainerModel.objects.with_deleted()
            .filter(id=container_id, user_id=user_id)
            .values(*_REFERENCE_FIELDS)
            .afirst()
        )
        if container_row is None:
            raise MoneyContainerNotFoundError(container_id)

        return _container_ref(container_row)

    async def resolve_many(
        self,
        container_ids: list[UUID],
        user_id: int,
    ) -> dict[UUID, MoneyContainerRef]:
        container_rows = (
            MoneyContainerModel.objects.with_deleted()
            .filter(id__in=set(container_ids), user_id=user_id)
            .values(*_REFERENCE_FIELDS)
        )

        return {row["id"]: _container_ref(row) async for row in container_rows}


def _container_ref(row: dict) -> MoneyContainerRef:
    return MoneyContainerRef(
        id=row["id"],
        kind=MoneyContainerKind(row["kind"]),
        currency_code=row["currency_id"],
        title=row["name"],
        is_closed=row["deleted_at"] is not None,
    )
