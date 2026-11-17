from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from kafka_messages import CategoryUpdated

from data_write_core.infrastructure.messaging import datetime_to_timestamp

from ...dtos import CategoryDTO, category_to_dto
from ._category_command_base import CategoryCommandHandlerBase

UNCHANGED_WRITE_VERSION = 0


@dataclass(frozen=True)
class UpdateCategoryCommand:
    user_id: int
    user_external_id: str
    category_id: UUID
    name: str


class UpdateCategoryCommandHandler(CategoryCommandHandlerBase):
    async def handle(self, command: UpdateCategoryCommand) -> tuple[CategoryDTO, int]:
        category = await self._load_editable_category(command.category_id, command.user_id)

        new_name = command.name.strip()
        await self._ensure_name_free(
            command.user_id,
            category.kind,
            new_name,
            excluding_category_id=command.category_id,
        )

        previous_name = category.name
        previous_updated_at = category.updated_at
        moment = datetime.now()
        if not category.rename(new_name, moment):
            return category_to_dto(category), UNCHANGED_WRITE_VERSION

        async def persist_rename() -> None:
            await self._category_repository.save_category(category)

        async def undo_rename() -> None:
            category.rename(previous_name, previous_updated_at or moment)
            await self._category_repository.save_category(category)

        write_version = await self._run_category_saga(
            forward_action=persist_rename,
            compensate_action=undo_rename,
            category=category,
            event=CategoryUpdated(
                category_id=category.unique_id,
                user_id=command.user_id,
                kind=str(category.kind),
                previous_name=previous_name,
                new_name=category.name,
                updated_at=datetime_to_timestamp(moment),
            ),
            partition_key=command.user_external_id,
        )

        return category_to_dto(category), write_version
