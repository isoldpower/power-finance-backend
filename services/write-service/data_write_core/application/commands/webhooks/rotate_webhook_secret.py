from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist
from kafka_messages import WebhookSecretRotated

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

from ...bootstrap import get_repository_registry
from ...dtos import WebhookWithSecretDTO, webhook_to_secret_dto
from ...interfaces import OutboxRepository, WebhookRepository
from ..command_base import CommandHandlerBase


@dataclass(frozen=True)
class RotateWebhookSecretCommand:
    user_id: int
    user_external_id: str
    webhook_id: UUID


class RotateWebhookSecretCommandHandler(CommandHandlerBase[WebhookWithSecretDTO]):
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

    async def handle(self, command: RotateWebhookSecretCommand) -> tuple[WebhookWithSecretDTO, int]:
        try:
            webhook = await self._webhook_repository.get_user_webhook_by_id(
                command.webhook_id,
                command.user_id,
            )
        except ObjectDoesNotExist as exc:
            raise WebhookNotFoundError(command.webhook_id) from exc

        timestamp_now = datetime.now()
        previous_secret = webhook.secret
        webhook.rotate_secret(now=timestamp_now)

        write_version = await self._run_transactions_saga(
            webhook,
            previous_secret=previous_secret,
            timestamp=timestamp_now,
            partition_key=command.user_external_id,
        )

        await self._publish_domain_events(webhook)
        return webhook_to_secret_dto(webhook), write_version

    async def _run_transactions_saga(
        self,
        webhook: WebhookEntity,
        previous_secret: str,
        timestamp: datetime,
        partition_key: str,
    ) -> int:
        persist_rotation, undo_rotation = self._get_save_unsave_lambdas(
            webhook,
            previous_secret=previous_secret,
        )

        saga_coordinator = FinalizedSagaCoordinator(
            transaction_steps=[
                PostgresWriteStep(
                    forward_action=persist_rotation,
                    compensate_action=undo_rotation,
                ),
            ],
            final_step=PostgresOutboxEmissionStep(
                outbox_repository=self._outbox_repository,
                entries=[
                    build_outbox_entry(
                        WebhookSecretRotated(
                            webhook_id=webhook.unique_id,
                            user_id=int(webhook.user_id),
                            secret=webhook.secret,
                            rotated_at=datetime_to_timestamp(timestamp),
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
        previous_secret: str,
    ) -> tuple[PostgresAction, PostgresAction]:
        async def persist_rotation() -> None:
            await self._webhook_repository.save_webhook(webhook)

        async def undo_rotation() -> None:
            webhook.restore_secret(previous_secret, datetime.now())
            await self._webhook_repository.save_webhook(webhook)

        return persist_rotation, undo_rotation
