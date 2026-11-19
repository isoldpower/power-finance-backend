from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from kafka_messages import CategoryCreated

from data_write_core.domain.entities import CategoryEntity
from data_write_core.domain.value_objects import CategoryKind
from data_write_core.infrastructure.messaging import datetime_to_timestamp

from ...dtos import CategoryDTO, category_to_dto
from ._category_command_base import CategoryCommandHandlerBase


@dataclass(frozen=True)
class CreateCategoryCommand:
    user_id: int
    user_external_id: str
    kind: CategoryKind
    name: str


class CreateCategoryCommandHandler(CategoryCommandHandlerBase):
    async def handle(self, command: CreateCategoryCommand) -> tuple[CategoryDTO, int]:
        category_name = command.name.strip()
        await self._ensure_name_free(command.user_id, command.kind, category_name)

        new_category = CategoryEntity.create_owned(
            id=uuid4(),
            kind=command.kind,
            name=category_name,
            user_id=str(command.user_id),
            created_at=datetime.now(),
        )

        async def persist_category() -> None:
            await self._category_repository.create_category(new_category)

        async def undo_persisted_category() -> None:
            await self._category_repository.hard_delete_category(UUID(new_category.unique_id))

        write_version = await self._run_category_saga(
            forward_action=persist_category,
            compensate_action=undo_persisted_category,
            category=new_category,
            event=CategoryCreated(
                category_id=new_category.unique_id,
                user_id=command.user_id,
                kind=str(new_category.kind),
                name=new_category.name,
                created_at=datetime_to_timestamp(new_category.created_at),
            ),
            partition_key=command.user_external_id,
        )

        return category_to_dto(new_category), write_version
