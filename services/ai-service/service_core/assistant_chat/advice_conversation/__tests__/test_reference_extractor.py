"""Turning a finished reply into the chips beside it.

Against a real Postgres because the whole job is a lookup: an extractor that
resolved ids without asking the database would cite things that do not exist.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from service_core.shared.db_connection import (
    AccountModel,
    ProjectedTransaction,
    UserModel,
    get_session_factory,
    session_scope,
)

from ..contracts import ConnectionContext
from ..references import ProjectedReferenceExtractor

OWNER = ConnectionContext(path="/api/v1/chat/advice", external_id="clerk_7")
STRANGER_EXTERNAL_ID = "clerk_9"
NOON = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)


def _extractor() -> ProjectedReferenceExtractor:
    return ProjectedReferenceExtractor(get_session_factory())


async def _user(user_id: int, external_id: str) -> int:
    async with session_scope() as session:
        session.add(UserModel(user_id=user_id, external_id=external_id, created_at=NOON))

    return user_id


async def _transaction(user_id: int, deleted: bool = False):
    transaction_id = uuid4()
    async with session_scope() as session:
        session.add(
            ProjectedTransaction(
                id=transaction_id,
                user_id=user_id,
                container_id=uuid4(),
                container_kind="wallet",
                amount=Decimal("-4.20"),
                currency_code="USD",
                created_at=NOON,
                deleted_at=NOON if deleted else None,
            )
        )

    return transaction_id


async def _account(user_id: int):
    account_id = uuid4()
    async with session_scope() as session:
        session.add(
            AccountModel(
                id=account_id,
                user_id=user_id,
                group="assets",
                name=f"Cash {account_id}",
                created_at=NOON,
            )
        )

    return account_id


async def test_a_reply_that_cites_nothing_has_no_references():
    await _user(1, OWNER.external_id)

    assert await _extractor().extract("You spent more on dining.", OWNER) == ()


async def test_a_transaction_the_user_owns_is_cited():
    user_id = await _user(1, OWNER.external_id)
    transaction_id = await _transaction(user_id)

    references = await _extractor().extract(f"See {transaction_id}.", OWNER)

    assert [(reference.type, reference.id) for reference in references] == [
        ("transaction", transaction_id)
    ]


async def test_an_account_the_user_owns_is_cited():
    user_id = await _user(1, OWNER.external_id)
    account_id = await _account(user_id)

    references = await _extractor().extract(f"Account {account_id}.", OWNER)

    assert [reference.type for reference in references] == ["account"]


async def test_another_users_records_are_never_cited():
    """A reply cannot be talked into citing someone else's records — the id is
    dropped rather than resolved."""

    await _user(1, OWNER.external_id)
    stranger_id = await _user(2, STRANGER_EXTERNAL_ID)
    transaction_id = await _transaction(stranger_id)

    assert await _extractor().extract(f"See {transaction_id}.", OWNER) == ()


async def test_an_unknown_id_is_dropped_rather_than_guessed_at():
    """A chip that deep-links nowhere is worse than no chip."""

    await _user(1, OWNER.external_id)

    assert await _extractor().extract(f"See {uuid4()}.", OWNER) == ()


async def test_a_deleted_transaction_is_not_cited():
    user_id = await _user(1, OWNER.external_id)
    transaction_id = await _transaction(user_id, deleted=True)

    assert await _extractor().extract(f"See {transaction_id}.", OWNER) == ()


async def test_the_same_id_twice_is_cited_once():
    user_id = await _user(1, OWNER.external_id)
    transaction_id = await _transaction(user_id)

    references = await _extractor().extract(f"Both {transaction_id} and {transaction_id}.", OWNER)

    assert len(references) == 1


async def test_references_keep_the_order_they_are_mentioned_in():
    user_id = await _user(1, OWNER.external_id)
    first = await _transaction(user_id)
    second = await _transaction(user_id)

    references = await _extractor().extract(f"{second} then {first}", OWNER)

    assert [reference.id for reference in references] == [second, first]


async def test_a_user_who_has_not_synced_yet_cites_nothing():
    """The conversation can start before `UserSynced` arrives. Nothing is
    resolvable yet, which is not an error."""

    assert await _extractor().extract(f"See {uuid4()}.", OWNER) == ()
