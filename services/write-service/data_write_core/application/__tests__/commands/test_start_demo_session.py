from datetime import UTC, datetime, timedelta

import jwt
import pytest

from data_write_core.application.commands.demo import (
    StartDemoSessionCommand,
    StartDemoSessionCommandHandler,
)
from data_write_core.application.interfaces.demo_token_issuer import IssuedDemoToken
from data_write_core.domain.entities import InternalUserEntity
from data_write_core.domain.value_objects.demo_identity import (
    DEMO_EXTERNAL_ID_PREFIX,
    is_demo_external_id,
    new_demo_external_id,
)
from data_write_core.infrastructure.demo import DEMO_TOKEN_ALGORITHM, JwtDemoTokenIssuer

DEMO_SECRET = "test-demo-secret-that-is-long-enough-0000"
DEMO_ISSUER = "power-finance-demo"
PROVISIONED_USER_ID = 41


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

    async def seed(self, user_id: int, external_id: str) -> None:
        self.seeded_accounts.append((user_id, external_id))


class FixedTokenIssuer:
    def __init__(self) -> None:
        self.issued_for: list[str] = []

    def issue(self, external_id: str) -> IssuedDemoToken:
        self.issued_for.append(external_id)
        return IssuedDemoToken(token="signed-token", expires_at=datetime(2030, 1, 1, tzinfo=UTC))


def test_a_new_demo_identity_is_random_and_recognisable():
    first_identity = new_demo_external_id()
    second_identity = new_demo_external_id()

    assert first_identity.startswith(DEMO_EXTERNAL_ID_PREFIX)
    assert first_identity != second_identity
    assert is_demo_external_id(first_identity)


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


async def test_starting_a_session_provisions_seeds_and_signs_one_fresh_demo_user():
    user_repository = RecordingUserRepository()
    seeder = RecordingSeeder()
    token_issuer = FixedTokenIssuer()

    demo_session = await StartDemoSessionCommandHandler(
        token_issuer=token_issuer,
        user_repository=user_repository,
        account_seeder=seeder,
    ).handle(StartDemoSessionCommand())

    assert is_demo_external_id(demo_session.external_id)
    assert user_repository.provisioned_external_ids == [demo_session.external_id]
    assert seeder.seeded_accounts == [(PROVISIONED_USER_ID, demo_session.external_id)]
    assert token_issuer.issued_for == [demo_session.external_id]
    assert demo_session.token == "signed-token"


async def test_every_session_gets_its_own_demo_user():
    user_repository = RecordingUserRepository()

    for _ in range(2):
        await StartDemoSessionCommandHandler(
            token_issuer=FixedTokenIssuer(),
            user_repository=user_repository,
            account_seeder=RecordingSeeder(),
        ).handle(StartDemoSessionCommand())

    first_identity, second_identity = user_repository.provisioned_external_ids
    assert first_identity != second_identity
