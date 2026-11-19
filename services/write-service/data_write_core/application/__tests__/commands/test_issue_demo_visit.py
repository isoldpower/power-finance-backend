from datetime import UTC, datetime, timedelta

from data_write_core.application.commands.demo import (
    IssueDemoVisitCommand,
    IssueDemoVisitCommandHandler,
)
from data_write_core.infrastructure.demo import HmacDemoVisitCodec

DEMO_SESSION_SECRET = "a-demo-session-secret-of-at-least-32-characters"
ISSUED_AT = datetime(2026, 11, 15, 12, 0, 0, tzinfo=UTC)
VISIT_LIFETIME = timedelta(hours=24)
ROTATION_WINDOW = timedelta(minutes=5)


class InMemoryVisitRegistry:
    def __init__(self) -> None:
        self.active_visits: dict[str, tuple[str, datetime]] = {}

    async def claim_active_visit(self, client_address, candidate_identifier, hold_until) -> str:
        active_visit = self.active_visits.setdefault(
            client_address, (candidate_identifier, hold_until)
        )
        return active_visit[0]

    async def replace_active_visit(self, client_address, identifier, hold_until) -> None:
        self.active_visits[client_address] = (identifier, hold_until)


def _handler(registry: InMemoryVisitRegistry, moment: datetime = ISSUED_AT):
    return IssueDemoVisitCommandHandler(
        visit_codec=HmacDemoVisitCodec(
            secret=DEMO_SESSION_SECRET,
            lifetime=VISIT_LIFETIME,
            clock=lambda: moment,
        ),
        visit_registry=registry,
        rotation_window=ROTATION_WINDOW,
    )


async def test_the_first_visit_of_a_client_is_issued_and_held_until_the_rotation_window():
    registry = InMemoryVisitRegistry()

    issued_visit = await _handler(registry).handle(IssueDemoVisitCommand("203.0.113.7"))

    assert registry.active_visits["203.0.113.7"] == (
        issued_visit.identifier,
        issued_visit.expires_at - ROTATION_WINDOW,
    )


async def test_a_client_asking_again_gets_its_active_visit_back():
    registry = InMemoryVisitRegistry()
    first_visit = await _handler(registry).handle(IssueDemoVisitCommand("203.0.113.7"))

    repeated_visit = await _handler(registry, ISSUED_AT + timedelta(hours=3)).handle(
        IssueDemoVisitCommand("203.0.113.7")
    )

    assert repeated_visit == first_visit


async def test_another_client_gets_its_own_visit():
    registry = InMemoryVisitRegistry()
    first_visit = await _handler(registry).handle(IssueDemoVisitCommand("203.0.113.7"))

    other_visit = await _handler(registry).handle(IssueDemoVisitCommand("198.51.100.4"))

    assert other_visit.nonce != first_visit.nonce


async def test_an_unverifiable_held_visit_is_replaced_with_a_fresh_one():
    registry = InMemoryVisitRegistry()
    registry.active_visits["203.0.113.7"] = ("dv1_signed-with-a-rotated-secret", ISSUED_AT)

    issued_visit = await _handler(registry).handle(IssueDemoVisitCommand("203.0.113.7"))

    assert issued_visit.identifier.startswith("dv1_")
    assert registry.active_visits["203.0.113.7"][0] == issued_visit.identifier
