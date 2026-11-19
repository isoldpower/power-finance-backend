from collections.abc import Collection
from uuid import UUID

from data_write_core.application.interfaces import DemoSeedRepository
from data_write_core.infrastructure.orm import (
    DemoAccountSeedModel,
    MoneyContainerModel,
    TransactionModel,
)


class DjangoDemoSeedRepository(DemoSeedRepository):
    async def is_seed_completed(self, user_id: int) -> bool:
        return await DemoAccountSeedModel.objects.filter(user_id=user_id).aexists()

    async def mark_seed_completed(self, user_id: int) -> None:
        await DemoAccountSeedModel.objects.aget_or_create(user_id=user_id)

    async def find_existing_seed_items(
        self,
        user_id: int,
        candidate_item_ids: Collection[UUID],
    ) -> set[UUID]:
        existing_item_ids: set[UUID] = set()
        async for container_id in (
            MoneyContainerModel.objects.with_deleted()
            .filter(user_id=user_id, id__in=candidate_item_ids)
            .values_list("id", flat=True)
        ):
            existing_item_ids.add(container_id)
        async for transaction_id in TransactionModel.objects.filter(
            user_id=user_id, id__in=candidate_item_ids
        ).values_list("id", flat=True):
            existing_item_ids.add(transaction_id)

        return existing_item_ids
