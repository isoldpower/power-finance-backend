from dataclasses import dataclass
from datetime import datetime
from typing import Any

from filter_grammar_py import Record, matches, policy_for

from ..automations.vocabulary import subject_of
from ..events import EventCollector
from ._entity_root import EntityRoot


@dataclass(frozen=True)
class AutomationTrigger:
    type: str
    event: str | None = None
    schedule: str | None = None
    filter_body: dict[str, Any] | None = None


@dataclass(frozen=True)
class AutomationEffect:
    type: str
    params: dict[str, Any]


@dataclass(frozen=True)
class AutomationState:
    name: str
    icon: str
    enabled: bool
    trigger: AutomationTrigger
    effects: tuple[AutomationEffect, ...]
    updated_at: datetime | None
    deleted_at: datetime | None


class AutomationEntity(EntityRoot):
    def __init__(
        self,
        id: str,
        user_id: str,
        user_external_id: str,
        name: str,
        trigger: AutomationTrigger,
        effects: tuple[AutomationEffect, ...],
        created_at: datetime,
        icon: str = "",
        enabled: bool = True,
        last_run_at: datetime | None = None,
        runs: int = 0,
        updated_at: datetime | None = None,
        deleted_at: datetime | None = None,
        event_collector: EventCollector | None = None,
    ):
        super().__init__(unique_id=id, collector=event_collector or EventCollector())

        self._user_id = user_id
        self._user_external_id = user_external_id
        self._name = name
        self._icon = icon
        self._enabled = enabled
        self._trigger = trigger
        self._effects = effects
        self._last_run_at = last_run_at
        self._runs = runs
        self._created_at = created_at
        self._updated_at = updated_at
        self._deleted_at = deleted_at

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def user_external_id(self) -> str:
        return self._user_external_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def icon(self) -> str:
        return self._icon

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def trigger(self) -> AutomationTrigger:
        return self._trigger

    @property
    def effects(self) -> tuple[AutomationEffect, ...]:
        return self._effects

    @property
    def last_run_at(self) -> datetime | None:
        return self._last_run_at

    @property
    def runs(self) -> int:
        return self._runs

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime | None:
        return self._updated_at

    @property
    def deleted_at(self) -> datetime | None:
        return self._deleted_at

    @property
    def is_deleted(self) -> bool:
        return self._deleted_at is not None

    def matches_subject(self, subject: Record) -> bool:
        return matches(
            self._trigger.filter_body,
            subject,
            policy_for(subject_of(self._trigger.type)),
        )

    def snapshot(self) -> AutomationState:
        return AutomationState(
            name=self._name,
            icon=self._icon,
            enabled=self._enabled,
            trigger=self._trigger,
            effects=self._effects,
            updated_at=self._updated_at,
            deleted_at=self._deleted_at,
        )

    def restore(self, state: AutomationState) -> None:
        self._name = state.name
        self._icon = state.icon
        self._enabled = state.enabled
        self._trigger = state.trigger
        self._effects = state.effects
        self._updated_at = state.updated_at
        self._deleted_at = state.deleted_at

    def rename(self, name: str | None, icon: str | None) -> None:
        self._name = name if name is not None else self._name
        self._icon = icon if icon is not None else self._icon

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def replace_trigger(self, trigger: AutomationTrigger) -> None:
        self._trigger = trigger

    def replace_effects(self, effects: tuple[AutomationEffect, ...]) -> None:
        self._effects = effects

    def touch(self, at: datetime) -> None:
        self._updated_at = at

    def soft_delete(self, at: datetime) -> None:
        self._deleted_at = at
        self._updated_at = at

    def record_run(self, at: datetime) -> None:
        self._runs += 1
        self._last_run_at = at
