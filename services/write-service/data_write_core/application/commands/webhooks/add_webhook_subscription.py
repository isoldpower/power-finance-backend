from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from django.core.exceptions import ObjectDoesNotExist
from kafka_messages import WebhookSubscriptionAdded

from data_write_core.domain.entities import WebhookSubscriptionEntity
from data_write_core.domain.exceptions import (
    DuplicateWebhookSubscriptionError,
    UnsupportedWebhookEventTypeError,
    WebhookNotFoundError,
)
from data_write_core.domain.value_objects import WebhookType
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
class AddWebhookSubscriptionCommand:
    user_id: int
    user_external_id: str
    webhook_id: UUID
    event_type: str


class AddWebhookSubscriptionCommandHandler(CommandHandlerBase[WebhookSubscriptionDTO]):
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
        self, command: AddWebhookSubscriptionCommand
    ) -> tuple[WebhookSubscriptionDTO, int]:
        if not WebhookType.is_supported(command.event_type):
            raise UnsupportedWebhookEventTypeError(command.event_type)

        try:
            webhook = await self._webhook_repository.get_user_webhook_by_id(
                command.webhook_id,
                command.user_id,
            )
        except ObjectDoesNotExist as exc:
            raise WebhookNotFoundError(command.webhook_id) from exc

        if await self._webhook_repository.subscription_exists(
            command.webhook_id,
            command.event_type,
        ):
            raise DuplicateWebhookSubscriptionError(command.webhook_id, command.event_type)

        new_subscription = WebhookSubscriptionEntity(
            id=str(uuid4()),
            webhook_id=webhook.unique_id,
            event_type=command.event_type,
            created_at=datetime.now(),
        )
        persisted_subscription, write_version = await self._run_transactions_saga(
            new_subscription,
            user_id=command.user_id,
            partition_key=command.user_external_id,
        )

        await self._publish_domain_events(new_subscription)
        return webhook_subscription_to_dto(persisted_subscription), write_version

    async def _run_transactions_saga(
        self,
        new_subscription: WebhookSubscriptionEntity,
        user_id: int,
        partition_key: str,
    ) -> tuple[WebhookSubscriptionEntity, int]:
        subscription_holder: dict[str, WebhookSubscriptionEntity] = {}
        persist_subscription, undo_persisted_subscription = self._get_save_unsave_lambdas(
            subscription_holder=subscription_holder,
            created_subscription=new_subscription,
        )

        saga_coordinator = FinalizedSagaCoordinator(
            transaction_steps=[
                PostgresWriteStep(
                    forward_action=persist_subscription,
                    compensate_action=undo_persisted_subscription,
                ),
            ],
            final_step=PostgresOutboxEmissionStep(
                outbox_repository=self._outbox_repository,
                entries=[
                    build_outbox_entry(
                        WebhookSubscriptionAdded(
                            subscription_id=new_subscription.unique_id,
                            webhook_id=new_subscription.webhook_id,
                            user_id=user_id,
                            event_type=new_subscription.event_type,
                            created_at=datetime_to_timestamp(new_subscription.created_at),
                        ),
                        aggregate_type="webhook",
                        aggregate_id=new_subscription.webhook_id,
                        partition_key=partition_key,
                    )
                ],
            ),
        )

        outbox_version = await saga_coordinator.run_transaction()
        return subscription_holder["subscription"], outbox_version

    def _get_save_unsave_lambdas(
        self,
        subscription_holder: dict[str, WebhookSubscriptionEntity],
        created_subscription: WebhookSubscriptionEntity,
    ) -> tuple[PostgresAction, PostgresAction]:
        async def persist_subscription() -> None:
            subscription_holder[
                "subscription"
            ] = await self._webhook_repository.create_subscription(created_subscription)

        async def undo_persisted_subscription() -> None:
            await self._webhook_repository.hard_delete_subscription(
                UUID(created_subscription.unique_id),
            )

        return persist_subscription, undo_persisted_subscription
