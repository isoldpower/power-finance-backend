from dataclasses import dataclass
from datetime import timedelta

from ...interfaces.demo_visit_codec import DemoVisit, DemoVisitCodec
from ...interfaces.demo_visit_registry import DemoVisitRegistry


@dataclass(frozen=True)
class IssueDemoVisitCommand:
    client_address: str


class IssueDemoVisitCommandHandler:
    def __init__(
        self,
        visit_codec: DemoVisitCodec,
        visit_registry: DemoVisitRegistry,
        rotation_window: timedelta,
    ) -> None:
        self._visit_codec = visit_codec
        self._visit_registry = visit_registry
        self._rotation_window = rotation_window

    async def handle(self, command: IssueDemoVisitCommand) -> DemoVisit:
        candidate_visit = self._visit_codec.issue()
        hold_until = candidate_visit.expires_at - self._rotation_window
        active_identifier = await self._visit_registry.claim_active_visit(
            command.client_address,
            candidate_visit.identifier,
            hold_until,
        )
        if active_identifier == candidate_visit.identifier:
            return candidate_visit

        active_visit = self._visit_codec.verify(active_identifier)
        if active_visit is not None:
            return active_visit

        await self._visit_registry.replace_active_visit(
            command.client_address,
            candidate_visit.identifier,
            hold_until,
        )
        return candidate_visit
