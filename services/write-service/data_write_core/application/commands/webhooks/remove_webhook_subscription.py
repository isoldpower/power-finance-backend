from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist
from kafka_messages import WebhookSubscriptionRemoved

from data_write_core.domain.entities import WebhookSubscriptionEntity
from data_write_core.domain.exceptions import (
    WebhookNotFoundError,
    WebhookSubscriptionNotFoundError,
)
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
from ...dtos import WebhookSubscriptionDTO, webhook_subscription_to_dto
from ...interfaces import OutboxRepository, WebhookRepository
from ..command_base import CommandHandlerBase


@dataclass(frozen=True)
class RemoveWebhookSubscriptionCommand:
    user_id: int
    user_external_id: str
    webhook_id: UUID
    subscription_id: UUID


class RemoveWebhookSubscriptionCommandHandler(CommandHandlerBase[WebhookSubscriptionDTO]):
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

    async def handle(
        self, command: RemoveWebhookSubscriptionCommand
    ) -> tuple[WebhookSubscriptionDTO, int]:
        try:
            await self._webhook_repository.get_user_webhook_by_id(
                command.webhook_id,
                command.user_id,
            )
        except ObjectDoesNotExist as exc:
            raise WebhookNotFoundError(command.webhook_id) from exc

        try:
            subscription = await self._webhook_repository.get_webhook_subscription_by_id(
                command.subscription_id,
                command.webhook_id,
            )
        except ObjectDoesNotExist as exc:
            raise WebhookSubscriptionNotFoundError(command.subscription_id) from exc

        write_version = await self._run_transactions_saga(
            subscription,
            user_id=command.user_id,
            partition_key=command.user_external_id,
        )

        await self._publish_domain_events(subscription)
        return webhook_subscription_to_dto(subscription), write_version

    async def _run_transactions_saga(
        self,
        subscription: WebhookSubscriptionEntity,
        user_id: int,
        partition_key: str,
    ) -> int:
        delete_subscription, restore_subscription = self._get_save_unsave_lambdas(subscription)
        removed_at = datetime.now(UTC)

        saga_coordinator = FinalizedSagaCoordinator(
            transaction_steps=[
                PostgresWriteStep(
                    forward_action=delete_subscription,
                    compensate_action=restore_subscription,
                ),
            ],
            final_step=PostgresOutboxEmissionStep(
                outbox_repository=self._outbox_repository,
                entries=[
                    build_outbox_entry(
                        WebhookSubscriptionRemoved(
                            subscription_id=subscription.unique_id,
                            webhook_id=subscription.webhook_id,
                            user_id=user_id,
                            removed_at=datetime_to_timestamp(removed_at),
                        ),
                        aggregate_type="webhook",
                        aggregate_id=subscription.webhook_id,
                        partition_key=partition_key,
                    )
                ],
            ),
        )

        return await saga_coordinator.run_transaction()

    def _get_save_unsave_lambdas(
        self,
        subscription: WebhookSubscriptionEntity,
    ) -> tuple[PostgresAction, PostgresAction]:
        async def delete_subscription() -> None:
            await self._webhook_repository.hard_delete_subscription(
                UUID(subscription.unique_id),
            )

        async def restore_subscription() -> None:
            await self._webhook_repository.create_subscription(subscription)

        return delete_subscription, restore_subscription
