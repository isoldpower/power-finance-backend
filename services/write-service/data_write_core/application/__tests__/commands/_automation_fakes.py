from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from data_write_core.application.interfaces import EffectExecutor
from data_write_core.domain.automations import RunContext
from data_write_core.domain.entities import (
    AutomationEffect,
    AutomationEntity,
    AutomationTrigger,
)

USER_ID = 7
EXTERNAL_ID = "user_abc"


class FakeAutomationRepository:
    def __init__(self, automations: list[AutomationEntity] | None = None) -> None:
        self.automations = list(automations or [])
        self.claims: list[tuple[str, str]] = []
        self.recorded: list[str] = []

    async def list_live_for_event(self, user_id: int, event: str) -> list[AutomationEntity]:
        return [
            rule
            for rule in self._live()
            if rule.trigger.type == "event"
            and rule.trigger.event == event
            and int(rule.user_id) == user_id
        ]

    async def list_live_scheduled(self, schedule: str) -> list[AutomationEntity]:
        return [
            rule
            for rule in self._live()
            if rule.trigger.type == "schedule" and rule.trigger.schedule == schedule
        ]

    async def claim_run(
        self,
        automation_id: UUID,
        user_id: int,
        run_key: str,
        at: datetime,
    ) -> bool:
        claim = (str(automation_id), run_key)
        if claim in self.claims:
            return False

        self.claims.append(claim)

        return True

    async def record_run(self, automation_id: UUID, at: datetime) -> int:
        self.recorded.append(str(automation_id))

        return self.recorded.count(str(automation_id))

    def _live(self) -> list[AutomationEntity]:
        return sorted(
            (rule for rule in self.automations if rule.enabled and rule.deleted_at is None),
            key=lambda rule: (rule.created_at, rule.unique_id),
        )


class FakeOutboxRepository:
    def __init__(self) -> None:
        self.entries: list = []

    async def get_latest_sequence(self) -> int:
        return 42

    async def append(self, entry) -> int:
        self.entries.append(entry)

        return 42


class RecordingEffect(EffectExecutor):
    """Stands in for the real executors, which reach into four other slices."""

    def __init__(self, name: str, log: list[tuple[str, str]], fails: bool = False) -> None:
        self.name = name
        self.log = log
        self.fails = fails

    async def apply(self, params: dict[str, Any], context: RunContext) -> None:
        self.log.append((self.name, context.automation_id))
        if self.fails:
            raise RuntimeError(f"{self.name} failed")


def make_rule(
    *,
    effects: tuple[str, ...] = ("notify",),
    filter_body: dict[str, Any] | None = None,
    trigger_type: str = "event",
    event: str | None = "transaction.created",
    schedule: str | None = None,
    created_at: datetime | None = None,
    name: str = "Rule",
    enabled: bool = True,
    user_id: int = USER_ID,
) -> AutomationEntity:
    return AutomationEntity(
        id=str(uuid4()),
        user_id=str(user_id),
        user_external_id=EXTERNAL_ID,
        name=name,
        trigger=AutomationTrigger(
            type=trigger_type,
            event=event if trigger_type == "event" else None,
            schedule=schedule if trigger_type == "schedule" else None,
            filter_body=filter_body,
        ),
        effects=tuple(AutomationEffect(type=kind, params={}) for kind in effects),
        created_at=created_at or datetime(2026, 1, 1),
        enabled=enabled,
    )
