from typing import Any

from data_write_core.domain.automations import RunContext
from data_write_core.domain.entities import ActionSource
from data_write_core.domain.value_objects import (
    ActionResolution,
    ResolutionIntent,
)

from .....interfaces import EffectExecutor
from ....actions.raise_action import (
    RaiseActionCommand,
    RaiseActionCommandHandler,
)

AUTOMATION_KIND = "automation"

AUTOMATION_RESOLUTIONS: tuple[ActionResolution, ...] = (
    ActionResolution(
        resolution_id="acknowledge",
        label="Got it",
        intent=ResolutionIntent.PRIMARY,
        applies=False,
    ),
    ActionResolution(
        resolution_id="dismiss",
        label="Ignore",
        intent=ResolutionIntent.SECONDARY,
        applies=False,
        dismissal=True,
    ),
)


class RaiseActionEffect(EffectExecutor):
    async def apply(self, params: dict[str, Any], context: RunContext) -> None:
        subject_type, subject_id = context.subject

        await RaiseActionCommandHandler().handle(
            RaiseActionCommand(
                user_id=context.user_id,
                user_external_id=context.user_external_id,
                source=ActionSource.SCHEDULER,
                kind=AUTOMATION_KIND,
                severity=str(params["severity"]),
                title=str(params["title"]),
                body=str(params["body"]),
                subject_type=subject_type,
                subject_id=subject_id,
                group_key=f"automation:{context.automation_id}",
                resolutions=AUTOMATION_RESOLUTIONS,
            )
        )
