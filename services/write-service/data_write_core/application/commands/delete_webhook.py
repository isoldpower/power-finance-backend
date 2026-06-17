from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist
from kafka_messages import WebhookEndpointDeleted

from data_write_core.domain.entities import WebhookEntity
from data_write_core.domain.exceptions import WebhookNotFoundError
from data_write_core.infrastructure.messaging import (
    build_outbox_entry,
    datetime_to_timestamp,
)
from data_write_core.infrastructure.outbox_saga import (
    FinalizedSagaCoordinator,
    PostgresAction,
    PostgresOutboxEmissionStep,
    PostgresWriteStep,
)

from ..bootstrap import get_repository_registry
from ..dtos import WebhookDTO, webhook_to_dto
from ..interfaces import OutboxRepository, WebhookRepository
from ._command_base import CommandHandlerBase


@dataclass(frozen=True)
class DeleteWebhookCommand:
    user_id: int
    user_external_id: str
    webhook_id: UUID


class DeleteWebhookCommandHandler(CommandHandlerBase[WebhookDTO]):
    _webhook_repository: WebhookRepository
    _outbox_repository: OutboxRepository

    def __init__(
        self,
        webhook_repository: WebhookRepository | None = None,
        outbox_repository: OutboxRepository | None = None,
    ) -> None:
        if webhook_repository is None or outbox_repository is None:
            registry = get_repository_registry()
            webhook_repository = webhook_repository or registry.webhook_repository
            outbox_repository = outbox_repository or registry.outbox_repository

        self._webhook_repository = webhook_repository
        self._outbox_repository = outbox_repository

    async def handle(self, command: DeleteWebhookCommand) -> tuple[WebhookDTO, int]:
        try:
            webhook = await self._webhook_repository.get_user_webhook_by_id(
                command.webhook_id,
                command.user_id,
            )
        except ObjectDoesNotExist as exc:
            raise WebhookNotFoundError(command.webhook_id) from exc

        write_version = await self._run_transactions_saga(
            webhook,
            partition_key=command.user_external_id,
        )

        await self._publish_domain_events(webhook)
        return webhook_to_dto(webhook), write_version

    async def _run_transactions_saga(
        self,
        webhook: WebhookEntity,
        partition_key: str,
    ) -> int:
        delete_webhook, restore_webhook = self._get_save_unsave_lambdas(webhook)
        deleted_at = datetime.now(UTC)

        saga_coordinator = FinalizedSagaCoordinator(
            transaction_steps=[
                PostgresWriteStep(
                    forward_action=delete_webhook,
                    compensate_action=restore_webhook,
                ),
            ],
            final_step=PostgresOutboxEmissionStep(
                outbox_repository=self._outbox_repository,
                entries=[
                    build_outbox_entry(
                        WebhookEndpointDeleted(
                            webhook_id=webhook.unique_id,
                            user_id=int(webhook.user_id),
                            deleted_at=datetime_to_timestamp(deleted_at),
                        ),
                        aggregate_type="webhook",
                        aggregate_id=webhook.unique_id,
                        partition_key=partition_key,
                    )
                ],
            ),
        )

        return await saga_coordinator.run_transaction()

    def _get_save_unsave_lambdas(
        self,
        webhook: WebhookEntity,
    ) -> tuple[PostgresAction, PostgresAction]:
        async def delete_webhook() -> None:
            await self._webhook_repository.hard_delete_webhook(UUID(webhook.unique_id))

        async def restore_webhook() -> None:
            await self._webhook_repository.create_webhook(webhook)

        return delete_webhook, restore_webhook
