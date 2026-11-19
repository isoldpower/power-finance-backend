from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from kafka_messages import CategoryDeleted

from data_write_core.infrastructure.messaging import datetime_to_timestamp

from ...dtos import CategoryDTO, category_to_dto
from ._category_command_base import CategoryCommandHandlerBase


@dataclass(frozen=True)
class DeleteCategoryCommand:
    user_id: int
    user_external_id: str
    category_id: UUID


class DeleteCategoryCommandHandler(CategoryCommandHandlerBase):
    async def handle(self, command: DeleteCategoryCommand) -> tuple[CategoryDTO, int]:
        category = await self._load_editable_category(command.category_id, command.user_id)

        moment = datetime.now()
        category.mark_deleted(moment)

        async def persist_deletion() -> None:
            await self._category_repository.save_category(category)

        async def undo_deletion() -> None:
            category.restore(datetime.now())
            await self._category_repository.save_category(category)

        write_version = await self._run_category_saga(
            forward_action=persist_deletion,
            compensate_action=undo_deletion,
            category=category,
            event=CategoryDeleted(
                category_id=category.unique_id,
                user_id=command.user_id,
                kind=str(category.kind),
                deleted_at=datetime_to_timestamp(moment),
            ),
            partition_key=command.user_external_id,
        )

        return category_to_dto(category), write_version
