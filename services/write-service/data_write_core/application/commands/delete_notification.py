from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist
from kafka_messages import NotificationDeleted

from data_write_core.domain.entities import NotificationEntity
from data_write_core.domain.exceptions import NotificationNotFoundError
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
from ..dtos import NotificationDTO, notification_to_dto
from ..interfaces import NotificationRepository, OutboxRepository
from ._command_base import CommandHandlerBase


@dataclass(frozen=True)
class DeleteNotificationCommand:
    user_id: int
    user_external_id: str
    notification_id: UUID


class DeleteNotificationCommandHandler(CommandHandlerBase[NotificationDTO]):
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

    async def handle(self, command: DeleteNotificationCommand) -> tuple[NotificationDTO, int]:
        try:
            notification = await self._notification_repository.get_user_notification_by_id(
                command.notification_id,
                command.user_id,
            )
        except ObjectDoesNotExist as exc:
            raise NotificationNotFoundError(command.notification_id) from exc

        write_version = await self._run_transactions_saga(
            notification,
            partition_key=command.user_external_id,
        )

        await self._publish_domain_events(notification)
        return notification_to_dto(notification), write_version

    async def _run_transactions_saga(
        self,
        notification: NotificationEntity,
        partition_key: str,
    ) -> int:
        delete_notification, restore_notification = self._get_save_unsave_lambdas(notification)
        deleted_at = datetime.now(UTC)

        saga_coordinator = FinalizedSagaCoordinator(
            transaction_steps=[
                PostgresWriteStep(
                    forward_action=delete_notification,
                    compensate_action=restore_notification,
                ),
            ],
            final_step=PostgresOutboxEmissionStep(
                outbox_repository=self._outbox_repository,
                entries=[
                    build_outbox_entry(
                        NotificationDeleted(
                            notification_id=notification.unique_id,
                            user_id=int(notification.user_id),
                            deleted_at=datetime_to_timestamp(deleted_at),
                        ),
                        aggregate_type="notification",
                        aggregate_id=notification.unique_id,
                        partition_key=partition_key,
                    )
                ],
            ),
        )

        return await saga_coordinator.run_transaction()

    def _get_save_unsave_lambdas(
        self,
        notification: NotificationEntity,
    ) -> tuple[PostgresAction, PostgresAction]:
        async def delete_notification() -> None:
            await self._notification_repository.hard_delete_notification(
                UUID(notification.unique_id),
            )

        async def restore_notification() -> None:
            await self._notification_repository.create_notification(notification)

        return delete_notification, restore_notification
