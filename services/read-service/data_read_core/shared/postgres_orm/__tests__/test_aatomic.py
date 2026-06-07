"""aatomic — async transaction wrapper commits on success, rolls back on error."""

from datetime import UTC, datetime

import pytest

from data_read_core.shared.postgres_orm import WalletReadModel, aatomic

pytestmark = pytest.mark.django_db(transaction=True)

WALLET_ID = "11111111-1111-1111-1111-111111111111"


async def _insert_wallet() -> None:
    await WalletReadModel.objects.acreate(
        id=WALLET_ID,
        user_id=7,
        title="Main",
        currency_code="USD",
        balance=0,
        created_at=datetime.now(UTC),
        updated_at=None,
    )


async def test_commits_on_success():
    async with aatomic():
        await _insert_wallet()

    assert await WalletReadModel.objects.filter(id=WALLET_ID).aexists()


async def test_rolls_back_on_exception():
    with pytest.raises(RuntimeError):
        async with aatomic():
            await _insert_wallet()
            raise RuntimeError("boom after insert")

    assert not await WalletReadModel.objects.filter(id=WALLET_ID).aexists()
