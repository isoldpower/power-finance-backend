from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from kafka_messages import WebhookEndpointCreated

from data_write_core.domain.entities import WebhookEntity
from data_write_core.domain.entities.webhook import generate_webhook_secret
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
class CreateWebhookCommand:
    user_id: int
    user_external_id: str
    title: str
    url: str


class CreateWebhookCommandHandler(CommandHandlerBase[WebhookWithSecretDTO]):
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

    async def handle(self, command: CreateWebhookCommand) -> tuple[WebhookWithSecretDTO, int]:
        timestamp_now = datetime.now()
        new_webhook = WebhookEntity(
            id=str(uuid4()),
            title=command.title.strip(),
            url=command.url.strip(),
            secret=generate_webhook_secret(),
            user_id=str(command.user_id),
            created_at=timestamp_now,
            updated_at=timestamp_now,
        )
        persisted_webhook, write_version = await self._run_transactions_saga(
            new_webhook,
            partition_key=command.user_external_id,
        )

        await self._publish_domain_events(new_webhook)
        return webhook_to_secret_dto(persisted_webhook), write_version

    async def _run_transactions_saga(
        self,
        new_webhook: WebhookEntity,
        partition_key: str,
    ) -> tuple[WebhookEntity, int]:
        webhook_holder: dict[str, WebhookEntity] = {}
        persist_webhook, undo_persisted_webhook = self._get_save_unsave_lambdas(
            webhook_holder=webhook_holder,
            created_webhook=new_webhook,
        )

        saga_coordinator = FinalizedSagaCoordinator(
            transaction_steps=[
                PostgresWriteStep(
                    forward_action=persist_webhook,
                    compensate_action=undo_persisted_webhook,
                ),
            ],
            final_step=PostgresOutboxEmissionStep(
                outbox_repository=self._outbox_repository,
                entries=[
                    build_outbox_entry(
                        WebhookEndpointCreated(
                            webhook_id=new_webhook.unique_id,
                            user_id=int(new_webhook.user_id),
                            title=new_webhook.title,
                            url=new_webhook.url,
                            secret=new_webhook.secret,
                            created_at=datetime_to_timestamp(new_webhook.created_at),
                        ),
                        aggregate_type="webhook",
                        aggregate_id=new_webhook.unique_id,
                        partition_key=partition_key,
                    )
                ],
            ),
        )

        outbox_version = await saga_coordinator.run_transaction()
        return webhook_holder["webhook"], outbox_version

    def _get_save_unsave_lambdas(
        self,
        webhook_holder: dict[str, WebhookEntity],
        created_webhook: WebhookEntity,
    ) -> tuple[PostgresAction, PostgresAction]:
        async def persist_webhook() -> None:
            webhook_holder["webhook"] = await self._webhook_repository.create_webhook(
                created_webhook,
            )

        async def undo_persisted_webhook() -> None:
            await self._webhook_repository.hard_delete_webhook(
                UUID(created_webhook.unique_id),
            )

        return persist_webhook, undo_persisted_webhook
