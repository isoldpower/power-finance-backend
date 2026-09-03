"""Filter material for the reads the gateway can reroute to this service.

Kept out of `queries` on purpose. A cursor is bound to the filters that
produced it, so these dataclasses are the one thing on the write side that a
cross-service test has to be able to read — and importing `queries` boots the
repository registry, which opens an ImmuDB connection. Nothing here touches
infrastructure.
"""

from dataclasses import dataclass

from data_write_core.domain.entities import ActionStatus

STATUS_PARAM = "status"
SOURCE_PARAM = "source"
SEVERITY_PARAM = "severity"
ENABLED_PARAM = "enabled"


@dataclass(frozen=True)
class FallbackActionFilters:
    status: str = ActionStatus.PENDING
    source: str | None = None
    severity: str | None = None

    def as_cursor_material(self) -> dict:
        """The material read-service binds an action cursor to. A cursor minted
        there arrives here unchanged, so this dict must be byte-identical to the
        read side's or the fingerprint check rejects a page the client can
        already see."""

        return {
            STATUS_PARAM: self.status,
            SOURCE_PARAM: self.source,
            SEVERITY_PARAM: self.severity,
        }


@dataclass(frozen=True)
class FallbackAutomationFilters:
    enabled: bool | None = None

    def as_cursor_material(self) -> dict:
        """Byte-identical to the read side's, for the same reason."""

        return {ENABLED_PARAM: self.enabled}
