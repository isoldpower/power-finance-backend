from dataclasses import dataclass

from data_write_core.application.config import ParamsList
from data_write_core.domain.entities import ActionStatus


@dataclass(frozen=True)
class FallbackActionFilters:
    status: str = ActionStatus.PENDING
    source: str | None = None
    severity: str | None = None

    def as_cursor_material(self) -> dict:
        return {
            ParamsList.STATUS: self.status,
            ParamsList.SOURCE: self.source,
            ParamsList.SEVERITY: self.severity,
        }


@dataclass(frozen=True)
class FallbackAutomationFilters:
    enabled: bool | None = None

    def as_cursor_material(self) -> dict:
        return {ParamsList.ENABLED: self.enabled}
