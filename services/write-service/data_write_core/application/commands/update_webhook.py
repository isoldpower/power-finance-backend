from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist
from kafka_messages import WebhookEndpointUpdated

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
class UpdateWebhookCommand:
    user_id: int
    user_external_id: str
    webhook_id: UUID
    title: str | None = None
    url: str | None = None


class UpdateWebhookCommandHandler(CommandHandlerBase[WebhookDTO]):
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

    async def handle(self, command: UpdateWebhookCommand) -> tuple[WebhookDTO, int]:
        webhook = await self._load_webhook(command)

        timestamp_now = datetime.now()
        previous_title, previous_url = webhook.title, webhook.url
        webhook.update(now=timestamp_now, title=command.title, url=command.url)

        write_version = await self._run_transactions_saga(
            webhook,
            previous_title=previous_title,
            previous_url=previous_url,
            timestamp=timestamp_now,
            partition_key=command.user_external_id,
        )

        await self._publish_domain_events(webhook)
        return webhook_to_dto(webhook), write_version

    async def _load_webhook(self, command: UpdateWebhookCommand) -> WebhookEntity:
        try:
            return await self._webhook_repository.get_user_webhook_by_id(
                command.webhook_id,
                command.user_id,
            )
        except ObjectDoesNotExist as exc:
            raise WebhookNotFoundError(command.webhook_id) from exc

    async def _run_transactions_saga(
        self,
        webhook: WebhookEntity,
        previous_title: str,
        previous_url: str,
        timestamp: datetime,
        partition_key: str,
    ) -> int:
        persist_update, undo_update = self._get_save_unsave_lambdas(
            webhook,
            previous_title=previous_title,
            previous_url=previous_url,
        )

        saga_coordinator = FinalizedSagaCoordinator(
            transaction_steps=[
                PostgresWriteStep(
                    forward_action=persist_update,
                    compensate_action=undo_update,
                ),
            ],
            final_step=PostgresOutboxEmissionStep(
                outbox_repository=self._outbox_repository,
                entries=[
                    build_outbox_entry(
                        WebhookEndpointUpdated(
                            webhook_id=webhook.unique_id,
                            user_id=int(webhook.user_id),
                            title=webhook.title,
                            url=webhook.url,
                            updated_at=datetime_to_timestamp(timestamp),
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
        previous_title: str,
        previous_url: str,
    ) -> tuple[PostgresAction, PostgresAction]:
        async def persist_update() -> None:
            await self._webhook_repository.save_webhook(webhook)

        async def undo_update() -> None:
            webhook.update(now=datetime.now(), title=previous_title, url=previous_url)
            await self._webhook_repository.save_webhook(webhook)

        return persist_update, undo_update
