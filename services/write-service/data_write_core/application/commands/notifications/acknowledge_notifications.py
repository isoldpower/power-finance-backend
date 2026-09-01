from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from kafka_messages import NotificationsAcknowledged

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

from ...bootstrap import get_repository_registry
from ...dtos import NotificationDTO, notification_to_dto
from ...interfaces import NotificationRepository, OutboxRepository
from ..command_base import CommandHandlerBase


@dataclass(frozen=True)
class AcknowledgeNotificationsCommand:
    user_id: int
    user_external_id: str
    notification_ids: tuple[UUID, ...]
    strict: bool = False


class AcknowledgeNotificationsCommandHandler(CommandHandlerBase[list[NotificationDTO]]):
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

    async def handle(
        self,
        command: AcknowledgeNotificationsCommand,
    ) -> tuple[list[NotificationDTO], int]:
        requested_ids = list(command.notification_ids)
        found = await self._notification_repository.get_user_notifications_by_ids(
            requested_ids,
            command.user_id,
        )
        if command.strict:
            found_ids = {str(notification.unique_id) for notification in found}
            for requested_id in requested_ids:
                if str(requested_id) not in found_ids:
                    raise NotificationNotFoundError(requested_id)

        pending_notifications = [
            notification for notification in found if not notification.is_acknowledged
        ]
        if not pending_notifications:
            return (
                [notification_to_dto(notification) for notification in found],
                await self._outbox_repository.get_latest_sequence(),
            )

        acknowledged_at = datetime.now(UTC)
        for notification in pending_notifications:
            notification.acknowledge(acknowledged_at)

        write_version = await self._run_transactions_saga(
            [UUID(notification.unique_id) for notification in pending_notifications],
            user_id=command.user_id,
            partition_key=command.user_external_id,
            acknowledged_at=acknowledged_at,
        )

        return (
            [notification_to_dto(notification) for notification in found],
            write_version,
        )

    async def _run_transactions_saga(
        self,
        ids_to_ack: list[UUID],
        user_id: int,
        partition_key: str,
        acknowledged_at: datetime,
    ) -> int:
        mark_read, unmark_read = self._get_save_unsave_lambdas(
            ids_to_ack,
            user_id,
            acknowledged_at,
        )

        saga_coordinator = FinalizedSagaCoordinator(
            transaction_steps=[
                PostgresWriteStep(
                    forward_action=mark_read,
                    compensate_action=unmark_read,
                ),
            ],
            final_step=PostgresOutboxEmissionStep(
                outbox_repository=self._outbox_repository,
                entries=[
                    build_outbox_entry(
                        NotificationsAcknowledged(
                            notification_ids=[str(ack_id) for ack_id in ids_to_ack],
                            user_id=user_id,
                            acknowledged_at=datetime_to_timestamp(acknowledged_at),
                        ),
                        aggregate_type="notification",
                        aggregate_id=str(ids_to_ack[0]),
                        partition_key=partition_key,
                    )
                ],
            ),
        )

        return await saga_coordinator.run_transaction()

    def _get_save_unsave_lambdas(
        self,
        ids_to_ack: list[UUID],
        user_id: int,
        acknowledged_at: datetime,
    ) -> tuple[PostgresAction, PostgresAction]:
        async def mark_read() -> None:
            await self._notification_repository.acknowledge_notifications(
                ids_to_ack,
                user_id,
                acknowledged_at,
            )

        async def unmark_read() -> None:
            await self._notification_repository.unacknowledge_notifications(
                ids_to_ack,
                user_id,
            )

        return mark_read, unmark_read
