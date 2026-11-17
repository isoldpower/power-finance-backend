from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import jwt
import pytest

from data_write_core.application.commands.demo import (
    StartDemoSessionCommand,
    StartDemoSessionCommandHandler,
    demo_account_seed,
)
from data_write_core.application.commands.demo.demo_account_seed import (
    DEMO_TRANSACTIONS,
    DEMO_WALLETS,
    DemoAccountSeeder,
    demo_seed_item_id,
)
from data_write_core.application.interfaces.demo_token_issuer import IssuedDemoToken
from data_write_core.application.interfaces.demo_visit_codec import DemoVisit
from data_write_core.domain.entities import InternalUserEntity
from data_write_core.domain.value_objects.demo_identity import (
    DEMO_EXTERNAL_ID_PREFIX,
    demo_external_id_for_visit,
    is_demo_external_id,
)
from data_write_core.infrastructure.demo import DEMO_TOKEN_ALGORITHM, JwtDemoTokenIssuer

DEMO_SECRET = "test-demo-secret-that-is-long-enough-0000"
DEMO_ISSUER = "power-finance-demo"
PROVISIONED_USER_ID = 41
SEEDED_WRITE_VERSION = 913
VISIT_EXPIRES_AT = datetime(2030, 1, 1, tzinfo=UTC)


def _demo_visit(nonce: str = "q8n3V0kz5tX2bYp1mW7cRg") -> DemoVisit:
    return DemoVisit(identifier=f"dv1_{nonce}_x_y", nonce=nonce, expires_at=VISIT_EXPIRES_AT)


class RecordingUserRepository:
    def __init__(self) -> None:
        self.provisioned_external_ids: list[str] = []

    async def get_synced_internal(self, external_id: str) -> InternalUserEntity:
        self.provisioned_external_ids.append(external_id)
        return InternalUserEntity(
            user_id=str(PROVISIONED_USER_ID),
            external_id=external_id,
            email="",
            first_name="",
            last_name="",
        )


class RecordingSeeder:
    def __init__(self) -> None:
        self.seeded_accounts: list[tuple[int, str]] = []

    async def seed_if_incomplete(self, user_id: int, external_id: str) -> int | None:
        already_seeded = (user_id, external_id) in self.seeded_accounts
        self.seeded_accounts.append((user_id, external_id))
        return None if already_seeded else SEEDED_WRITE_VERSION


class FixedTokenIssuer:
    def __init__(self) -> None:
        self.issued_for: list[str] = []
        self.not_after_values: list[datetime | None] = []

    def issue(self, external_id: str, not_after: datetime | None = None) -> IssuedDemoToken:
        self.issued_for.append(external_id)
        self.not_after_values.append(not_after)
        return IssuedDemoToken(token="signed-token", expires_at=datetime(2030, 1, 1, tzinfo=UTC))


def test_a_visit_maps_to_one_stable_recognisable_demo_identity():
    first_identity = demo_external_id_for_visit("q8n3V0kz5tX2bYp1mW7cRg")

    assert first_identity.startswith(DEMO_EXTERNAL_ID_PREFIX)
    assert is_demo_external_id(first_identity)
    assert first_identity == demo_external_id_for_visit("q8n3V0kz5tX2bYp1mW7cRg")
    assert first_identity != demo_external_id_for_visit("Zx1Ql8fN2dS4uV6aB0cE3g")
    assert "q8n3V0kz5tX2bYp1mW7cRg" not in first_identity


@pytest.mark.parametrize("external_id", ["user_2abc", "demo_", "", "Demo_abc"])
def test_clerk_and_malformed_identities_are_not_demo_identities(external_id):
    assert not is_demo_external_id(external_id)


def test_the_issued_token_verifies_with_the_shared_secret_only():
    issued = JwtDemoTokenIssuer(
        secret=DEMO_SECRET,
        issuer=DEMO_ISSUER,
        lifetime=timedelta(hours=24),
    ).issue("demo_abc123")

    claims = jwt.decode(
        issued.token,
        DEMO_SECRET,
        algorithms=[DEMO_TOKEN_ALGORITHM],
        issuer=DEMO_ISSUER,
    )

    assert claims["sub"] == "demo_abc123"
    assert claims["exp"] == int(issued.expires_at.timestamp())
    assert jwt.get_unverified_header(issued.token)["alg"] == "HS256"
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(
            issued.token,
            "another-secret-that-is-also-long-enough-00",
            algorithms=[DEMO_TOKEN_ALGORITHM],
        )


def test_the_token_never_outlives_its_visit():
    visit_expires_at = datetime.now(UTC) + timedelta(minutes=10)

    issued = JwtDemoTokenIssuer(
        secret=DEMO_SECRET,
        issuer=DEMO_ISSUER,
        lifetime=timedelta(hours=24),
    ).issue("demo_abc123", not_after=visit_expires_at)

    assert issued.expires_at == visit_expires_at


def test_the_token_expires_after_the_configured_lifetime():
    before_issue = datetime.now(UTC)
    issued = JwtDemoTokenIssuer(
        secret=DEMO_SECRET,
        issuer=DEMO_ISSUER,
        lifetime=timedelta(hours=24),
    ).issue("demo_abc123")

    assert (
        timedelta(hours=23, minutes=59)
        < issued.expires_at - before_issue
        <= timedelta(hours=24, seconds=5)
    )


async def test_starting_a_session_provisions_seeds_and_signs_the_visit_demo_user():
    user_repository = RecordingUserRepository()
    seeder = RecordingSeeder()
    token_issuer = FixedTokenIssuer()
    demo_visit = _demo_visit()

    demo_session = await StartDemoSessionCommandHandler(
        token_issuer=token_issuer,
        user_repository=user_repository,
        account_seeder=seeder,
    ).handle(StartDemoSessionCommand(visit=demo_visit))

    assert demo_session.external_id == demo_external_id_for_visit(demo_visit.nonce)
    assert user_repository.provisioned_external_ids == [demo_session.external_id]
    assert seeder.seeded_accounts == [(PROVISIONED_USER_ID, demo_session.external_id)]
    assert token_issuer.issued_for == [demo_session.external_id]
    assert token_issuer.not_after_values == [VISIT_EXPIRES_AT]
    assert demo_session.token == "signed-token"
    assert demo_session.write_version == SEEDED_WRITE_VERSION


async def test_a_repeated_session_for_one_visit_reuses_the_account():
    user_repository = RecordingUserRepository()
    seeder = RecordingSeeder()
    handler = StartDemoSessionCommandHandler(
        token_issuer=FixedTokenIssuer(),
        user_repository=user_repository,
        account_seeder=seeder,
    )

    first_session = await handler.handle(StartDemoSessionCommand(visit=_demo_visit()))
    repeated_session = await handler.handle(StartDemoSessionCommand(visit=_demo_visit()))

    assert repeated_session.external_id == first_session.external_id
    assert first_session.write_version == SEEDED_WRITE_VERSION
    assert repeated_session.write_version is None


async def test_every_visit_gets_its_own_demo_user():
    user_repository = RecordingUserRepository()

    for nonce in ("q8n3V0kz5tX2bYp1mW7cRg", "Zx1Ql8fN2dS4uV6aB0cE3g"):
        await StartDemoSessionCommandHandler(
            token_issuer=FixedTokenIssuer(),
            user_repository=user_repository,
            account_seeder=RecordingSeeder(),
        ).handle(StartDemoSessionCommand(visit=_demo_visit(nonce)))

    first_identity, second_identity = user_repository.provisioned_external_ids
    assert first_identity != second_identity


SEED_ITEM_COUNT = len(DEMO_WALLETS) + 1 + len(DEMO_TRANSACTIONS)
SEEDED_EXTERNAL_ID = "demo_abc123"


class InMemorySeedRepository:
    def __init__(self, completed: bool = False) -> None:
        self.completed = completed
        self.existing_item_ids: set[UUID] = set()

    async def is_seed_completed(self, user_id: int) -> bool:
        return self.completed

    async def mark_seed_completed(self, user_id: int) -> None:
        self.completed = True

    async def find_existing_seed_items(self, user_id: int, candidate_item_ids) -> set[UUID]:
        return self.existing_item_ids & set(candidate_item_ids)


class RecordingCommandHandler:
    seed_repository: InMemorySeedRepository
    created_item_ids: list[UUID] = []
    failing_item_ids: set[UUID] = set()
    created_elsewhere_item_ids: set[UUID] = set()

    async def handle(self, command):
        item_id = getattr(command, "wallet_id", None)
        item_id = getattr(command, "goal_id", None) or item_id
        item_id = getattr(command, "transaction_id", None) or item_id
        if item_id in RecordingCommandHandler.created_elsewhere_item_ids:
            RecordingCommandHandler.seed_repository.existing_item_ids.add(item_id)
            raise RuntimeError("duplicate key")
        if item_id in RecordingCommandHandler.failing_item_ids:
            raise RuntimeError("immudb unreachable")

        RecordingCommandHandler.created_item_ids.append(item_id)
        RecordingCommandHandler.seed_repository.existing_item_ids.add(item_id)
        return SimpleNamespace(id=item_id), 100 + len(RecordingCommandHandler.created_item_ids)


@pytest.fixture
def seed_repository(monkeypatch) -> InMemorySeedRepository:
    repository = InMemorySeedRepository()
    RecordingCommandHandler.seed_repository = repository
    RecordingCommandHandler.created_item_ids = []
    RecordingCommandHandler.failing_item_ids = set()
    RecordingCommandHandler.created_elsewhere_item_ids = set()
    for handler_name in (
        "CreateNewWalletCommandHandler",
        "CreateNewGoalCommandHandler",
        "CreateTransactionCommandHandler",
    ):
        monkeypatch.setattr(demo_account_seed, handler_name, RecordingCommandHandler)

    return repository


def _planned_item_ids() -> list[UUID]:
    return [
        *(demo_seed_item_id(SEEDED_EXTERNAL_ID, f"wallet:{seed.key}") for seed in DEMO_WALLETS),
        demo_seed_item_id(SEEDED_EXTERNAL_ID, "goal:trip"),
        *(
            demo_seed_item_id(SEEDED_EXTERNAL_ID, f"transaction:{position}")
            for position in range(len(DEMO_TRANSACTIONS))
        ),
    ]


async def test_a_fresh_account_is_seeded_completely_and_marked_done(seed_repository):
    write_version = await DemoAccountSeeder(seed_repository).seed_if_incomplete(
        PROVISIONED_USER_ID, SEEDED_EXTERNAL_ID
    )

    assert RecordingCommandHandler.created_item_ids == _planned_item_ids()
    assert len(RecordingCommandHandler.created_item_ids) == SEED_ITEM_COUNT
    assert write_version == 100 + SEED_ITEM_COUNT
    assert seed_repository.completed


async def test_a_completed_account_is_not_seeded_again(seed_repository):
    seed_repository.completed = True

    write_version = await DemoAccountSeeder(seed_repository).seed_if_incomplete(
        PROVISIONED_USER_ID, SEEDED_EXTERNAL_ID
    )

    assert RecordingCommandHandler.created_item_ids == []
    assert write_version is None


async def test_a_failed_seed_stays_incomplete_and_the_retry_creates_only_what_is_missing(
    seed_repository,
):
    planned_item_ids = _planned_item_ids()
    RecordingCommandHandler.failing_item_ids = {planned_item_ids[6]}
    seeder = DemoAccountSeeder(seed_repository)

    with pytest.raises(RuntimeError):
        await seeder.seed_if_incomplete(PROVISIONED_USER_ID, SEEDED_EXTERNAL_ID)

    assert RecordingCommandHandler.created_item_ids == planned_item_ids[:6]
    assert not seed_repository.completed

    RecordingCommandHandler.failing_item_ids = set()
    write_version = await seeder.seed_if_incomplete(PROVISIONED_USER_ID, SEEDED_EXTERNAL_ID)

    assert RecordingCommandHandler.created_item_ids == planned_item_ids
    assert write_version == 100 + SEED_ITEM_COUNT
    assert seed_repository.completed


async def test_an_item_created_by_a_concurrent_request_is_skipped(seed_repository):
    planned_item_ids = _planned_item_ids()
    RecordingCommandHandler.created_elsewhere_item_ids = {planned_item_ids[0]}

    await DemoAccountSeeder(seed_repository).seed_if_incomplete(
        PROVISIONED_USER_ID, SEEDED_EXTERNAL_ID
    )

    assert RecordingCommandHandler.created_item_ids == planned_item_ids[1:]
    assert seed_repository.completed


def test_seed_item_ids_are_stable_per_account():
    assert demo_seed_item_id("demo_a", "wallet:savings") == demo_seed_item_id(
        "demo_a", "wallet:savings"
    )
    assert demo_seed_item_id("demo_a", "wallet:savings") != demo_seed_item_id(
        "demo_b", "wallet:savings"
    )
