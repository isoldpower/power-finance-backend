import logging
from datetime import UTC, datetime
from uuid import UUID

from data_write_core.domain.automations import RunContext
from data_write_core.domain.entities import AutomationEntity
from data_write_core.domain.services import select_matching_rules

from ....interfaces import AutomationRepository, EffectExecutor
from ...automations.record_run import (
    RecordAutomationRunCommand,
    RecordAutomationRunCommandHandler,
)
from .exceptions import UnknownEffectError
from .subject_loader import LoadedSubject

logger = logging.getLogger("data_write_core.automations")


class RuleRunner:
    def __init__(
        self,
        automation_repository: AutomationRepository,
        record_run_handler: RecordAutomationRunCommandHandler,
        executors: dict[str, EffectExecutor],
    ) -> None:
        self._automation_repository = automation_repository
        self._record_run_handler = record_run_handler
        self._executors = executors

    async def run(
        self,
        rules: list[AutomationEntity],
        subject: LoadedSubject,
        *,
        user_id: int,
        user_external_id: str,
        run_key: str,
    ) -> list[str]:
        selection = select_matching_rules(rules, subject.record)
        for skipped in selection.unreadable:
            logger.warning(
                "automations: rule %s has a condition its policy no longer accepts; skipping",
                skipped.unique_id,
            )

        applied: list[str] = []

        for rule in selection.matched:
            context = RunContext(
                user_id=user_id,
                user_external_id=user_external_id,
                automation_id=rule.unique_id,
                automation_name=rule.name,
                subject_type=subject.subject_type,
                subject_id=subject.subject_id,
            )
            if await self._run_one(rule, context, run_key):
                applied.append(rule.unique_id)

        return applied

    async def _run_one(
        self,
        rule: AutomationEntity,
        context: RunContext,
        run_key: str,
    ) -> bool:
        claimed = await self._automation_repository.claim_run(
            UUID(rule.unique_id),
            context.user_id,
            run_key,
            datetime.now(UTC),
        )
        if not claimed:
            return False

        try:
            await self._apply_effects(rule, context)
        except Exception:
            logger.exception(
                "automations: rule %s failed partway; earlier effects stand",
                rule.unique_id,
            )

            return False

        await self._record_run(context)

        return True

    async def _apply_effects(self, rule: AutomationEntity, context: RunContext) -> None:
        for effect in rule.effects:
            executor = self._executors.get(effect.type)
            if executor is None:
                raise UnknownEffectError(effect.type)

            await executor.apply(effect.params, context)

    async def _record_run(self, context: RunContext) -> None:
        await self._record_run_handler.handle(
            RecordAutomationRunCommand(
                user_id=context.user_id,
                user_external_id=context.user_external_id,
                automation_id=UUID(context.automation_id),
            )
        )
