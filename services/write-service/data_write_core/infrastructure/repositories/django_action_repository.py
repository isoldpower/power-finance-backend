from datetime import datetime
from uuid import UUID

from data_write_core.application.interfaces import ActionRepository
from data_write_core.domain.entities import ActionEntity, ActionStatus

from ..orm import ActionModel
from .mappers import ActionMapper


class DjangoActionRepository(ActionRepository):
    async def create_action(self, action: ActionEntity) -> ActionEntity:
        created_action = ActionModel()

        ActionMapper.apply_to_model(created_action, action)
        await created_action.asave()

        return ActionMapper.to_domain(await ActionModel.objects.aget(id=created_action.id))

    async def save_action(self, action: ActionEntity) -> ActionEntity:
        stored_action = await ActionModel.objects.aget(id=action.unique_id)

        ActionMapper.apply_to_model(stored_action, action)
        await stored_action.asave()

        return ActionMapper.to_domain(stored_action)

    async def get_user_action_by_id(self, action_id: UUID, user_id: int) -> ActionEntity:
        requested_action = await ActionModel.objects.aget(
            id=action_id,
            user_id=user_id,
        )

        return ActionMapper.to_domain(requested_action)

    async def find_pending_by_group_key(
        self,
        user_id: int,
        group_key: str,
    ) -> ActionEntity | None:
        found = await ActionModel.objects.filter(
            user_id=user_id,
            group_key=group_key,
            status=ActionStatus.PENDING,
        ).afirst()

        return ActionMapper.to_domain(found) if found else None

    async def hard_delete_action(self, action_id: UUID) -> None:
        await ActionModel.objects.filter(id=action_id).adelete()

    async def find_lapsed_pending(self, now: datetime, limit: int) -> list[ActionEntity]:
        queryset = ActionModel.objects.filter(
            status=ActionStatus.PENDING,
            expires_at__isnull=False,
            expires_at__lte=now,
        ).order_by("expires_at")[:limit]

        return [ActionMapper.to_domain(action) async for action in queryset]
