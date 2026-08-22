from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from kafka_messages import NotificationCreated

from data_write_core.domain.entities import NotificationEntity
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
from ...dtos import NotificationDTO, notification_to_dto
from ...interfaces import NotificationRepository, OutboxRepository
from ..command_base import CommandHandlerBase


@dataclass(frozen=True)
class CreateNotificationCommand:
    """System-authored notifications: issued by event consumers (e.g. the
    inbound notifications worker), never directly by HTTP clients."""

    user_id: int
    user_external_id: str
    short: str
    message: str
    payload: dict | None = None


class CreateNotificationCommandHandler(CommandHandlerBase[NotificationDTO]):
    _notification_repository: NotificationRepository
    _outbox_repository: OutboxRepository

    def __init__(
        self,
        notification_repository: NotificationRepository | None = None,
        outbox_repository: OutboxRepository | None = None,
    ) -> None:
        if notification_repository is None or outbox_repository is None:
            registry = get_repository_registry()
            notification_repository = notification_repository or registry.notification_repository
            outbox_repository = outbox_repository or registry.outbox_repository

        self._notification_repository = notification_repository
        self._outbox_repository = outbox_repository

    async def handle(self, command: CreateNotificationCommand) -> tuple[NotificationDTO, int]:
        new_notification = NotificationEntity(
            id=str(uuid4()),
            short=command.short,
            message=command.message,
            payload=command.payload,
            user_id=str(command.user_id),
            created_at=datetime.now(),
        )
        persisted_notification, write_version = await self._run_transactions_saga(
            new_notification,
            partition_key=command.user_external_id,
        )

        await self._publish_domain_events(new_notification)
        return notification_to_dto(persisted_notification), write_version

    async def _run_transactions_saga(
        self,
        new_notification: NotificationEntity,
        partition_key: str,
    ) -> tuple[NotificationEntity, int]:
        notification_holder: dict[str, NotificationEntity] = {}
        persist_notification, undo_persisted_notification = self._get_save_unsave_lambdas(
            notification_holder=notification_holder,
            created_notification=new_notification,
        )

        outbox_message = NotificationCreated(
            notification_id=new_notification.unique_id,
            user_id=int(new_notification.user_id),
            short=new_notification.short,
            message=new_notification.message,
            created_at=datetime_to_timestamp(new_notification.created_at),
        )
        if new_notification.payload is not None:
            outbox_message.payload.update(new_notification.payload)

        saga_coordinator = FinalizedSagaCoordinator(
            transaction_steps=[
                PostgresWriteStep(
                    forward_action=persist_notification,
                    compensate_action=undo_persisted_notification,
                ),
            ],
            final_step=PostgresOutboxEmissionStep(
                outbox_repository=self._outbox_repository,
                entries=[
                    build_outbox_entry(
                        outbox_message,
                        aggregate_type="notification",
                        aggregate_id=new_notification.unique_id,
                        partition_key=partition_key,
                    )
                ],
            ),
        )

        outbox_version = await saga_coordinator.run_transaction()
        return notification_holder["notification"], outbox_version

    def _get_save_unsave_lambdas(
        self,
        notification_holder: dict[str, NotificationEntity],
        created_notification: NotificationEntity,
    ) -> tuple[PostgresAction, PostgresAction]:
        async def persist_notification() -> None:
            notification_holder[
                "notification"
            ] = await self._notification_repository.create_notification(created_notification)

        async def undo_persisted_notification() -> None:
            await self._notification_repository.hard_delete_notification(
                UUID(created_notification.unique_id),
            )

        return persist_notification, undo_persisted_notification
