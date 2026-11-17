from uuid import UUID

from google.protobuf.message import Message

from data_write_core.domain.entities import CategoryEntity
from data_write_core.domain.exceptions import CategoryNameTakenError, CategoryNotFoundError
from data_write_core.domain.services import ensure_category_editable
from data_write_core.domain.value_objects import CategoryKind
from data_write_core.infrastructure.messaging import build_outbox_entry
from data_write_core.infrastructure.outbox_saga import (
    FinalizedSagaCoordinator,
    PostgresAction,
    PostgresOutboxEmissionStep,
    PostgresWriteStep,
)

from ...bootstrap import get_repository_registry
from ...dtos import CategoryDTO
from ...interfaces import CategoryRepository, OutboxRepository
from .._command_base import CommandHandlerBase

CATEGORY_AGGREGATE_TYPE = "category"


class CategoryCommandHandlerBase(CommandHandlerBase[CategoryDTO]):
    _category_repository: CategoryRepository
    _outbox_repository: OutboxRepository

    def __init__(
        self,
        category_repository: CategoryRepository | None = None,
        outbox_repository: OutboxRepository | None = None,
    ) -> None:
        if category_repository is None or outbox_repository is None:
            registry = get_repository_registry()
            category_repository = category_repository or registry.category_repository
            outbox_repository = outbox_repository or registry.outbox_repository

        self._category_repository = category_repository
        self._outbox_repository = outbox_repository

    async def _load_editable_category(self, category_id: UUID, user_id: int) -> CategoryEntity:
        category = await self._category_repository.get_visible_category(category_id, user_id)
        if category.deleted_at is not None:
            raise CategoryNotFoundError(category_id)

        ensure_category_editable(category)

        return category

    async def _ensure_name_free(
        self,
        user_id: int,
        kind: CategoryKind,
        name: str,
        excluding_category_id: UUID | None = None,
    ) -> None:
        if await self._category_repository.is_name_taken(
            user_id,
            kind,
            name,
            excluding_category_id=excluding_category_id,
        ):
            raise CategoryNameTakenError(name, str(kind))

    async def _run_category_saga(
        self,
        forward_action: PostgresAction,
        compensate_action: PostgresAction,
        category: CategoryEntity,
        event: Message,
        partition_key: str,
    ) -> int:
        saga_coordinator = FinalizedSagaCoordinator(
            transaction_steps=[
                PostgresWriteStep(
                    forward_action=forward_action,
                    compensate_action=compensate_action,
                ),
            ],
            final_step=PostgresOutboxEmissionStep(
                outbox_repository=self._outbox_repository,
                entries=[
                    build_outbox_entry(
                        event,
                        aggregate_type=CATEGORY_AGGREGATE_TYPE,
                        aggregate_id=category.unique_id,
                        partition_key=partition_key,
                    )
                ],
            ),
        )

        return await saga_coordinator.run_transaction()
