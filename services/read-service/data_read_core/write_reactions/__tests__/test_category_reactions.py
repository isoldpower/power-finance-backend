from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fakes import make_event
from google.protobuf.timestamp_pb2 import Timestamp
from kafka_messages import (
    CategoryCreated,
    CategoryDeleted,
    CategoryUpdated,
    TransactionCreated,
    TransactionMetadataUpdated,
    WalletCreated,
    WalletUpdated,
)

from data_read_core.shared.postgres_orm import (
    CategoryReadModel,
    TransactionReadModel,
    WalletReadModel,
)
from data_read_core.shared.redis_cache import get_redis
from data_read_core.write_reactions import (
    CreateCategoryReadModel,
    CreateTransactionReadModel,
    CreateWalletReadModel,
    EvictCategorisedItemCaches,
    RemoveCategoryReadModel,
    RenameCategoryReadModel,
    UpdateTransactionMetadataReadModel,
    UpdateWalletReadModel,
)
from data_read_core.write_reactions._cache_keys import (
    get_single_transaction_key,
    get_single_wallet_key,
)

pytestmark = pytest.mark.django_db(transaction=True)

USER_ID = 7
CATEGORY_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"
WALLET_ID = "11111111-1111-1111-1111-111111111111"
TRANSACTION_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
CREATED_AT = datetime(2026, 11, 1, 9, tzinfo=UTC)


def _timestamp(moment: datetime) -> Timestamp:
    timestamp = Timestamp()
    timestamp.FromDatetime(moment)
    return timestamp


async def _project_category(name: str = "Pets", kind: str = "transaction") -> None:
    await CreateCategoryReadModel().apply(
        make_event(
            CategoryCreated(
                category_id=CATEGORY_ID,
                user_id=USER_ID,
                kind=kind,
                name=name,
                created_at=_timestamp(CREATED_AT),
            )
        )
    )


async def test_a_created_category_is_projected_as_user_owned():
    await _project_category()

    category = await CategoryReadModel.objects.aget(id=CATEGORY_ID)
    assert category.name == "Pets"
    assert category.user_id == USER_ID
    assert category.is_global is False
    assert category.deleted_at is None


async def test_a_rename_changes_only_the_name():
    await _project_category()

    await RenameCategoryReadModel().apply(
        make_event(
            CategoryUpdated(
                category_id=CATEGORY_ID,
                user_id=USER_ID,
                kind="transaction",
                previous_name="Pets",
                new_name="Animals",
                updated_at=_timestamp(CREATED_AT),
            )
        )
    )

    category = await CategoryReadModel.objects.aget(id=CATEGORY_ID)
    assert category.name == "Animals"
    assert category.updated_at == CREATED_AT


async def test_a_deleted_category_keeps_its_row():
    await _project_category()

    await RemoveCategoryReadModel().apply(
        make_event(
            CategoryDeleted(
                category_id=CATEGORY_ID,
                user_id=USER_ID,
                kind="transaction",
                deleted_at=_timestamp(CREATED_AT),
            )
        )
    )

    category = await CategoryReadModel.objects.aget(id=CATEGORY_ID)
    assert category.deleted_at == CREATED_AT


async def _project_wallet(category_id: str = "") -> None:
    await CreateWalletReadModel().apply(
        make_event(
            WalletCreated(
                wallet_id=WALLET_ID,
                user_id=USER_ID,
                title="Main",
                currency_code="USD",
                created_at=_timestamp(CREATED_AT),
                category="Pets" if category_id else "",
                category_id=category_id,
                zero_balance="0",
            )
        )
    )


async def test_a_wallet_points_at_its_category():
    await _project_category(kind="wallet")
    await _project_wallet(CATEGORY_ID)

    wallet = await WalletReadModel.objects.select_related("category").aget(id=WALLET_ID)
    assert str(wallet.category_id) == CATEGORY_ID
    assert wallet.category.name == "Pets"


async def test_a_wallet_update_can_clear_its_category():
    await _project_category(kind="wallet")
    await _project_wallet(CATEGORY_ID)

    await UpdateWalletReadModel().apply(
        make_event(
            WalletUpdated(
                wallet_id=WALLET_ID,
                user_id=USER_ID,
                previous_title="Main",
                new_title="Main",
                updated_at=_timestamp(CREATED_AT),
                category="",
                category_id="",
                zero_balance="0",
            )
        )
    )

    wallet = await WalletReadModel.objects.aget(id=WALLET_ID)
    assert wallet.category_id is None


async def _project_transaction(category_id: str = "") -> None:
    await CreateTransactionReadModel().apply(
        make_event(
            TransactionCreated(
                transaction_id=TRANSACTION_ID,
                wallet_id=WALLET_ID,
                user_id=USER_ID,
                amount="-12.00",
                name="Vet",
                created_at=_timestamp(CREATED_AT),
                category="Pets" if category_id else "",
                category_id=category_id,
            )
        )
    )


async def test_a_transaction_points_at_its_category_and_metadata_moves_it():
    await _project_category()
    await _project_wallet()
    await _project_transaction(CATEGORY_ID)

    transaction = await TransactionReadModel.objects.aget(id=TRANSACTION_ID)
    assert str(transaction.category_id) == CATEGORY_ID

    other_category_id = str(uuid4())
    await UpdateTransactionMetadataReadModel().apply(
        make_event(
            TransactionMetadataUpdated(
                transaction_id=TRANSACTION_ID,
                user_id=USER_ID,
                name="Vet",
                category="Other",
                category_id=other_category_id,
                updated_at=_timestamp(CREATED_AT),
            )
        )
    )

    transaction = await TransactionReadModel.objects.aget(id=TRANSACTION_ID)
    assert str(transaction.category_id) == other_category_id


async def test_a_rename_evicts_the_cached_items_that_show_the_category():
    await _project_category()
    await _project_wallet()
    await _project_transaction(CATEGORY_ID)
    get_redis.cache_clear()
    redis_client = get_redis()
    await redis_client.set(get_single_transaction_key(TRANSACTION_ID), "cached")
    await redis_client.set(get_single_wallet_key(WALLET_ID), "cached")

    await EvictCategorisedItemCaches().apply(
        make_event(
            CategoryUpdated(
                category_id=CATEGORY_ID,
                user_id=USER_ID,
                kind="transaction",
                previous_name="Pets",
                new_name="Animals",
                updated_at=_timestamp(CREATED_AT),
            )
        )
    )

    assert await redis_client.get(get_single_transaction_key(TRANSACTION_ID)) is None
    assert await redis_client.get(get_single_wallet_key(WALLET_ID)) == "cached"
    await redis_client.delete(get_single_wallet_key(WALLET_ID))
    await redis_client.aclose()
    get_redis.cache_clear()
