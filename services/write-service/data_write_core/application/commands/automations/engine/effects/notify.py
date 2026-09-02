from typing import Any

from data_write_core.domain.automations import RunContext

from .....interfaces import EffectExecutor
from ....notifications.create_notification import (
    CreateNotificationCommand,
    CreateNotificationCommandHandler,
)


class NotifyEffect(EffectExecutor):
    async def apply(self, params: dict[str, Any], context: RunContext) -> None:
        subject_type, subject_id = context.subject

        await CreateNotificationCommandHandler().handle(
            CreateNotificationCommand(
                user_id=context.user_id,
                user_external_id=context.user_external_id,
                title=str(params["title"]),
                body=f"Raised by your rule “{context.automation_name}”.",
                severity=str(params["severity"]),
                subject_type=subject_type,
                subject_id=subject_id,
            )
        )
