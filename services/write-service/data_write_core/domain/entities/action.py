from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from ..events import EventCollector
from ..value_objects import ActionResolution
from ._entity_root import EntityRoot


class ActionSource(StrEnum):
    ASSISTANT = "assistant"
    SCHEDULER = "scheduler"


class ActionSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ActionStatus(StrEnum):
    PENDING = "pending"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    EXPIRED = "expired"


SEVERITY_RANKS: dict[str, int] = {
    ActionSeverity.INFO: 1,
    ActionSeverity.WARNING: 2,
    ActionSeverity.CRITICAL: 3,
}

ANSWERED_STATUSES = frozenset(
    {
        ActionStatus.RESOLVED,
        ActionStatus.DISMISSED,
        ActionStatus.EXPIRED,
    }
)


def rank_of(severity: str) -> int:
    return SEVERITY_RANKS.get(
        severity,
        SEVERITY_RANKS[ActionSeverity.INFO],
    )


class ActionEntity(EntityRoot):
    def __init__(
        self,
        id: str,
        user_id: str,
        user_external_id: str,
        source: str,
        kind: str,
        severity: str,
        title: str,
        body: str,
        created_at: datetime,
        resolutions: tuple[ActionResolution, ...] = (),
        status: str = ActionStatus.PENDING,
        subject_type: str | None = None,
        subject_id: str | None = None,
        money_amount: Decimal | None = None,
        money_currency: str | None = None,
        group_key: str | None = None,
        occurrences: int = 1,
        last_seen_at: datetime | None = None,
        expires_at: datetime | None = None,
        resolved_at: datetime | None = None,
        resolution_id: str | None = None,
        updated_at: datetime | None = None,
        event_collector: EventCollector | None = None,
    ):
        super().__init__(
            unique_id=id,
            collector=event_collector or EventCollector(),
        )

        self._user_id = user_id
        self._user_external_id = user_external_id
        self._source = source
        self._kind = kind
        self._severity = severity
        self._status = status
        self._title = title
        self._body = body
        self._subject_type = subject_type
        self._subject_id = subject_id
        self._money_amount = money_amount
        self._money_currency = money_currency
        self._group_key = group_key
        self._occurrences = occurrences
        self._last_seen_at = last_seen_at or created_at
        self._expires_at = expires_at
        self._resolved_at = resolved_at
        self._resolution_id = resolution_id
        self._resolutions = tuple(resolutions)
        self._created_at = created_at
        self._updated_at = updated_at

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def user_external_id(self) -> str:
        return self._user_external_id

    @property
    def source(self) -> str:
        return self._source

    @property
    def kind(self) -> str:
        return self._kind

    @property
    def severity(self) -> str:
        return self._severity

    @property
    def severity_rank(self) -> int:
        return rank_of(self._severity)

    @property
    def status(self) -> str:
        return self._status

    @property
    def title(self) -> str:
        return self._title

    @property
    def body(self) -> str:
        return self._body

    @property
    def subject_type(self) -> str | None:
        return self._subject_type

    @property
    def subject_id(self) -> str | None:
        return self._subject_id

    @property
    def money_amount(self) -> Decimal | None:
        return self._money_amount

    @property
    def money_currency(self) -> str | None:
        return self._money_currency

    @property
    def group_key(self) -> str | None:
        return self._group_key

    @property
    def occurrences(self) -> int:
        return self._occurrences

    @property
    def last_seen_at(self) -> datetime:
        return self._last_seen_at

    @property
    def expires_at(self) -> datetime | None:
        return self._expires_at

    @property
    def resolved_at(self) -> datetime | None:
        return self._resolved_at

    @property
    def resolution_id(self) -> str | None:
        return self._resolution_id

    @property
    def resolutions(self) -> tuple[ActionResolution, ...]:
        return self._resolutions

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime | None:
        return self._updated_at

    @property
    def is_answered(self) -> bool:
        return self._status in ANSWERED_STATUSES

    def resolution_by_id(self, resolution_id: str) -> ActionResolution | None:
        for resolution in self._resolutions:
            if resolution.resolution_id == resolution_id:
                return resolution

        return None

    def resolve(self, resolution: ActionResolution, at: datetime) -> None:
        self._status = ActionStatus.DISMISSED if resolution.dismissal else ActionStatus.RESOLVED
        self._resolution_id = resolution.resolution_id
        self._resolved_at = at
        self._updated_at = at
        self._resolutions = ()

    def expire(self, at: datetime) -> None:
        self._status = ActionStatus.EXPIRED
        self._resolved_at = at
        self._updated_at = at
        self._resolutions = ()

    def observe_again(self, at: datetime) -> None:
        self._occurrences += 1
        self._last_seen_at = at
        self._updated_at = at

    def restore_observation(
        self,
        occurrences: int,
        last_seen_at: datetime,
        updated_at: datetime | None,
    ) -> None:
        self._occurrences = occurrences
        self._last_seen_at = last_seen_at
        self._updated_at = updated_at
