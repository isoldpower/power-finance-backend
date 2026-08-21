from datetime import datetime
from decimal import Decimal
from uuid import UUID

import pytest
from write_service.common.pagination import CURSOR_CODEC, build_page

from data_write_core.application.exceptions import FallbackTransactionNotVisibleError
from data_write_core.application.queries import (
    GetFallbackTransactionQuery,
    GetFallbackTransactionQueryHandler,
    GetFallbackWalletQuery,
    GetFallbackWalletQueryHandler,
    ListFallbackTransactionsQuery,
    ListFallbackTransactionsQueryHandler,
    ListFallbackWalletsQuery,
    ListFallbackWalletsQueryHandler,
)

from .fakes import (
    FakeTransactionRepository,
    FakeWalletRepository,
    make_checkpoint,
    make_page,
    make_transaction,
    make_wallet,
)

WALLET_A = "11111111-1111-1111-1111-111111111111"
WALLET_B = "22222222-2222-2222-2222-222222222222"
TX_1 = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
TX_2 = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
TX_EFFECT = "cccccccc-cccc-cccc-cccc-cccccccccccc"


async def test_get_wallet_folds_unsettled_onto_checkpoint():
    wallet_repo = FakeWalletRepository([make_wallet(WALLET_A, currency="EUR")])
    transaction_repo = FakeTransactionRepository(
        checkpoints={WALLET_A: make_checkpoint(WALLET_A, "100", datetime(2026, 1, 1))},
        unsettled={
            WALLET_A: [
                make_transaction(TX_1, WALLET_A, "50"),
                make_transaction(TX_2, WALLET_A, "-20"),
            ]
        },
    )
    handler = GetFallbackWalletQueryHandler(wallet_repo, transaction_repo)

    wallet = await handler.handle(GetFallbackWalletQuery(user_id=7, wallet_id=UUID(WALLET_A)))

    assert wallet.balance_amount == Decimal("130")
    assert wallet.currency == "EUR"


async def test_get_wallet_with_no_checkpoint_starts_at_zero():
    wallet_repo = FakeWalletRepository([make_wallet(WALLET_A)])
    transaction_repo = FakeTransactionRepository(
        unsettled={WALLET_A: [make_transaction(TX_1, WALLET_A, "42")]},
    )
    handler = GetFallbackWalletQueryHandler(wallet_repo, transaction_repo)

    wallet = await handler.handle(GetFallbackWalletQuery(user_id=7, wallet_id=UUID(WALLET_A)))

    assert wallet.balance_amount == Decimal("42")


async def test_list_wallets_returns_dtos_with_balances_and_total():
    wallets = [
        make_wallet(WALLET_A, created_at=datetime(2026, 1, 2)),
        make_wallet(WALLET_B, created_at=datetime(2026, 1, 1)),
    ]
    wallet_repo = FakeWalletRepository(wallets)
    transaction_repo = FakeTransactionRepository(
        checkpoints={
            WALLET_A: make_checkpoint(WALLET_A, "10", datetime(2026, 1, 1)),
            WALLET_B: make_checkpoint(WALLET_B, "5", datetime(2026, 1, 1)),
        },
    )
    handler = ListFallbackWalletsQueryHandler(wallet_repo, transaction_repo)

    dtos, total = await handler.handle(
        ListFallbackWalletsQuery(user_id=7, page=make_page(limit=20))
    )

    assert total == 2
    assert [str(dto.id) for dto in dtos] == [WALLET_A, WALLET_B]
    assert dtos[0].balance_amount == Decimal("10")


async def test_list_wallets_pages_forward_from_a_cursor():
    """The second page starts after the first page's last row, not at an offset."""

    wallets = [
        make_wallet(WALLET_A, created_at=datetime(2026, 1, 2)),
        make_wallet(WALLET_B, created_at=datetime(2026, 1, 1)),
    ]
    handler = ListFallbackWalletsQueryHandler(
        FakeWalletRepository(wallets), FakeTransactionRepository()
    )

    first_request = make_page(limit=1)
    first_rows, total = await handler.handle(
        ListFallbackWalletsQuery(user_id=7, page=first_request)
    )
    first_page = build_page(first_rows, total, first_request)

    second_request = make_page(
        limit=1,
        cursor=CURSOR_CODEC.decode(first_page.next_cursor, first_request.fingerprint),
    )
    second_rows, _ = await handler.handle(ListFallbackWalletsQuery(user_id=7, page=second_request))

    assert total == 2
    assert [str(dto.id) for dto in first_page.items] == [WALLET_A]
    assert [str(dto.id) for dto in second_rows] == [WALLET_B]


async def test_get_transaction_resolves_currency_from_wallet():
    wallet_repo = FakeWalletRepository([make_wallet(WALLET_A, currency="GBP")])
    transaction = make_transaction(TX_1, WALLET_A, "12.50")
    transaction_repo = FakeTransactionRepository(user_transactions=[transaction])
    handler = GetFallbackTransactionQueryHandler(transaction_repo, wallet_repo)

    dto = await handler.handle(GetFallbackTransactionQuery(user_id=7, transaction_id=UUID(TX_1)))

    assert dto.currency_code == "GBP"
    assert dto.amount == Decimal("12.50")
    assert dto.source_wallet_id == WALLET_A


async def test_get_transaction_degrades_currency_when_wallet_gone():
    transaction = make_transaction(TX_1, WALLET_A, "12.50")
    handler = GetFallbackTransactionQueryHandler(
        FakeTransactionRepository(user_transactions=[transaction]),
        FakeWalletRepository([]),
    )

    dto = await handler.handle(GetFallbackTransactionQuery(user_id=7, transaction_id=UUID(TX_1)))

    assert dto.currency_code == ""


async def test_get_transaction_missing_raises():
    handler = GetFallbackTransactionQueryHandler(
        FakeTransactionRepository(), FakeWalletRepository([])
    )

    with pytest.raises(ValueError):
        await handler.handle(GetFallbackTransactionQuery(user_id=7, transaction_id=UUID(TX_1)))


async def test_list_transactions_sorts_desc_paginates_and_maps_currency():
    wallet_repo = FakeWalletRepository([make_wallet(WALLET_A, currency="USD")])
    older = make_transaction(TX_1, WALLET_A, "10", created_at=datetime(2026, 1, 1))
    newer = make_transaction(TX_2, WALLET_A, "20", created_at=datetime(2026, 1, 5))
    transaction_repo = FakeTransactionRepository(user_transactions=[older, newer])
    handler = ListFallbackTransactionsQueryHandler(transaction_repo, wallet_repo)

    dtos, total = await handler.handle(
        ListFallbackTransactionsQuery(user_id=7, page=make_page(limit=1))
    )

    assert total == 2
    assert str(dtos[0].id) == TX_2
    assert dtos[0].currency_code == "USD"


async def test_list_transactions_drops_cancelled_pair():
    wallet_repo = FakeWalletRepository([make_wallet(WALLET_A, currency="USD")])
    original = make_transaction(TX_1, WALLET_A, "20", created_at=datetime(2026, 1, 1))
    inverse = make_transaction(
        TX_EFFECT,
        WALLET_A,
        "-20",
        created_at=datetime(2026, 1, 2),
        cancels_other=UUID(TX_1),
    )
    handler = ListFallbackTransactionsQueryHandler(
        FakeTransactionRepository(user_transactions=[original, inverse]),
        wallet_repo,
    )

    dtos, total = await handler.handle(
        ListFallbackTransactionsQuery(user_id=7, page=make_page(limit=20))
    )

    assert total == 0
    assert dtos == []


async def test_list_transactions_folds_adjustment_into_original():
    wallet_repo = FakeWalletRepository([make_wallet(WALLET_A, currency="USD")])
    original = make_transaction(TX_1, WALLET_A, "20", created_at=datetime(2026, 1, 1))
    adjustment = make_transaction(
        TX_EFFECT,
        WALLET_A,
        "5",
        created_at=datetime(2026, 1, 2),
        adjusts_other=UUID(TX_1),
    )
    handler = ListFallbackTransactionsQueryHandler(
        FakeTransactionRepository(user_transactions=[original, adjustment]),
        wallet_repo,
    )

    dtos, total = await handler.handle(
        ListFallbackTransactionsQuery(user_id=7, page=make_page(limit=20))
    )

    assert total == 1
    assert str(dtos[0].id) == TX_1
    assert dtos[0].amount == Decimal("25")


async def test_get_transaction_folds_adjustment():
    wallet_repo = FakeWalletRepository([make_wallet(WALLET_A, currency="USD")])
    original = make_transaction(TX_1, WALLET_A, "20")
    adjustment = make_transaction(TX_EFFECT, WALLET_A, "5", adjusts_other=UUID(TX_1))
    handler = GetFallbackTransactionQueryHandler(
        FakeTransactionRepository(user_transactions=[original, adjustment]),
        wallet_repo,
    )

    dto = await handler.handle(GetFallbackTransactionQuery(user_id=7, transaction_id=UUID(TX_1)))

    assert dto.amount == Decimal("25")


async def test_get_transaction_cancelled_is_not_visible():
    """A cancelled transaction is gone as far as reads are concerned."""

    original = make_transaction(TX_1, WALLET_A, "20")
    inverse = make_transaction(TX_EFFECT, WALLET_A, "-20", cancels_other=UUID(TX_1))
    handler = GetFallbackTransactionQueryHandler(
        FakeTransactionRepository(user_transactions=[original, inverse]),
        FakeWalletRepository([make_wallet(WALLET_A)]),
    )

    with pytest.raises(FallbackTransactionNotVisibleError):
        await handler.handle(GetFallbackTransactionQuery(user_id=7, transaction_id=UUID(TX_1)))


async def test_get_transaction_effect_row_is_not_visible():
    inverse = make_transaction(TX_EFFECT, WALLET_A, "-20", cancels_other=UUID(TX_1))
    handler = GetFallbackTransactionQueryHandler(
        FakeTransactionRepository(user_transactions=[inverse]),
        FakeWalletRepository([make_wallet(WALLET_A)]),
    )

    with pytest.raises(FallbackTransactionNotVisibleError):
        await handler.handle(GetFallbackTransactionQuery(user_id=7, transaction_id=UUID(TX_EFFECT)))
