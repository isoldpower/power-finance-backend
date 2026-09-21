from datetime import datetime
from uuid import UUID

import pytest

from data_write_core.application.commands import (
    SoftDeleteWalletCommand,
    SoftDeleteWalletCommandHandler,
    UpdateExistingWalletCommand,
    UpdateExistingWalletCommandHandler,
)

from ..queries.fakes import FakeMoneyFlowRepository, FakeWalletRepository, make_wallet

pytestmark = pytest.mark.django_db(transaction=True)

WALLET_ID = "11111111-1111-1111-1111-111111111111"
USER_ID = 7
EXTERNAL_ID = "user_abc"


class FakeOutboxRepository:
    def __init__(self) -> None:
        self.entries: list = []

    async def get_latest_sequence(self) -> int:
        return 42

    async def append(self, entry) -> int:
        self.entries.append(entry)

        return 42


def build_soft_delete_handler(wallet_repository, outbox_repository):
    return SoftDeleteWalletCommandHandler(
        wallet_repository=wallet_repository,
        money_flow_repository=FakeMoneyFlowRepository(),
        outbox_repository=outbox_repository,
    )


async def test_soft_delete_marks_the_wallet_and_returns_the_outbox_version():
    wallet_repository = FakeWalletRepository([make_wallet(WALLET_ID)])
    outbox_repository = FakeOutboxRepository()

    wallet_dto, write_version = await build_soft_delete_handler(
        wallet_repository,
        outbox_repository,
    ).handle(
        SoftDeleteWalletCommand(
            user_id=USER_ID,
            user_external_id=EXTERNAL_ID,
            wallet_id=UUID(WALLET_ID),
        )
    )

    assert write_version == 42
    assert str(wallet_dto.id) == WALLET_ID
    assert wallet_repository.saved, "the soft delete should have been persisted"
    assert wallet_repository.saved[-1].deleted_at is not None


async def test_soft_delete_emits_one_wallet_deleted_entry_keyed_by_the_user():
    outbox_repository = FakeOutboxRepository()

    await build_soft_delete_handler(
        FakeWalletRepository([make_wallet(WALLET_ID)]),
        outbox_repository,
    ).handle(
        SoftDeleteWalletCommand(
            user_id=USER_ID,
            user_external_id=EXTERNAL_ID,
            wallet_id=UUID(WALLET_ID),
        )
    )

    assert len(outbox_repository.entries) == 1
    entry = outbox_repository.entries[0]
    assert entry.aggregate_type == "wallet"
    assert entry.aggregate_id == WALLET_ID
    assert entry.partition_key == EXTERNAL_ID


async def test_soft_delete_of_an_unknown_wallet_is_refused():
    outbox_repository = FakeOutboxRepository()

    with pytest.raises(LookupError):
        await build_soft_delete_handler(
            FakeWalletRepository([]),
            outbox_repository,
        ).handle(
            SoftDeleteWalletCommand(
                user_id=USER_ID,
                user_external_id=EXTERNAL_ID,
                wallet_id=UUID(WALLET_ID),
            )
        )

    assert outbox_repository.entries == [], "nothing may be emitted for a refused command"


async def test_update_renames_the_wallet_and_emits_an_update():
    wallet_repository = FakeWalletRepository([make_wallet(WALLET_ID, title="Before")])
    outbox_repository = FakeOutboxRepository()

    wallet_dto, write_version = await UpdateExistingWalletCommandHandler(
        wallet_repository=wallet_repository,
        money_flow_repository=FakeMoneyFlowRepository(),
        outbox_repository=outbox_repository,
    ).handle(
        UpdateExistingWalletCommand(
            user_id=USER_ID,
            user_external_id=EXTERNAL_ID,
            wallet_id=UUID(WALLET_ID),
            new_name="After",
        )
    )

    assert wallet_dto.name == "After"
    assert write_version == 42
    assert wallet_repository.saved[-1].title == "After"
    assert len(outbox_repository.entries) == 1
    assert outbox_repository.entries[0].aggregate_type == "wallet"


async def test_update_leaves_created_at_alone_and_moves_updated_at():
    created = datetime(2026, 1, 1)
    wallet_repository = FakeWalletRepository(
        [make_wallet(WALLET_ID, title="Before", created_at=created)]
    )

    await UpdateExistingWalletCommandHandler(
        wallet_repository=wallet_repository,
        money_flow_repository=FakeMoneyFlowRepository(),
        outbox_repository=FakeOutboxRepository(),
    ).handle(
        UpdateExistingWalletCommand(
            user_id=USER_ID,
            user_external_id=EXTERNAL_ID,
            wallet_id=UUID(WALLET_ID),
            new_name="After",
        )
    )

    saved = wallet_repository.saved[-1]
    assert saved.created_at == created
    assert saved.updated_at > created
