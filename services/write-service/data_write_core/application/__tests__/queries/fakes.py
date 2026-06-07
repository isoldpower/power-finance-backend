from datetime import datetime
from decimal import Decimal
from uuid import UUID

from data_write_core.domain.entities import (
    BalanceCheckpointEntity,
    TransactionEntity,
    WalletEntity,
)
from data_write_core.domain.value_objects import TransactionData, WalletData


def make_wallet(
    wallet_id: str,
    *,
    user_id: int = 7,
    currency: str = "USD",
    title: str = "Wallet",
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> WalletEntity:
    moment = created_at or datetime(2026, 1, 1)
    return WalletEntity.create(
        data=WalletData(title=title, currency_code=currency),
        id=wallet_id,
        user_id=str(user_id),
        created_at=moment,
        updated_at=updated_at or moment,
    )


def make_transaction(
    transaction_id: str,
    wallet_id: str,
    amount: str,
    *,
    user_id: int = 7,
    created_at: datetime | None = None,
    cancels_other: UUID | None = None,
    adjusts_other: UUID | None = None,
) -> TransactionEntity:
    return TransactionEntity.from_persistence(
        id=UUID(transaction_id),
        user_id=user_id,
        created_at=created_at or datetime(2026, 1, 1),
        data=TransactionData(
            source_wallet_id=UUID(wallet_id),
            amount=Decimal(amount),
            cancels_other=cancels_other,
            adjusts_other=adjusts_other,
        ),
    )


def make_checkpoint(wallet_id: str, balance: str, settled_at: datetime) -> BalanceCheckpointEntity:
    return BalanceCheckpointEntity(
        id=wallet_id,
        created_at=settled_at,
        balance=Decimal(balance),
    )


class FakeWalletRepository:
    def __init__(self, wallets: list[WalletEntity] | None = None) -> None:
        self._wallets = {str(wallet.unique_id): wallet for wallet in (wallets or [])}

    async def get_user_wallet_by_id(self, wallet_id, user_id: int) -> WalletEntity:
        wallet = self._wallets.get(str(wallet_id))
        if wallet is None:
            raise LookupError(f"wallet {wallet_id} not found")
        return wallet

    async def get_user_wallets(
        self, user_id: int, limit: int | None = None, offset: int | None = None
    ) -> list[WalletEntity]:
        ordered = sorted(
            self._wallets.values(),
            key=lambda wallet: wallet.created_at,
            reverse=True,
        )
        start = offset or 0
        if limit is not None:
            return ordered[start : start + limit]
        if offset is not None:
            return ordered[start:]
        return ordered

    async def count_user_wallets(self, user_id: int) -> int:
        return len(self._wallets)


class FakeTransactionRepository:
    def __init__(
        self,
        *,
        checkpoints: dict[str, BalanceCheckpointEntity] | None = None,
        unsettled: dict[str, list[TransactionEntity]] | None = None,
        user_transactions: list[TransactionEntity] | None = None,
    ) -> None:
        self._checkpoints = checkpoints or {}
        self._unsettled = unsettled or {}
        self._user_transactions = user_transactions or []
        self._by_id = {str(tx.unique_id): tx for tx in self._user_transactions}
        # Derived from the ledger so fakes mirror the real repo's queries.
        self._cancelling = {
            str(tx.cancels_other): tx
            for tx in self._user_transactions
            if tx.cancels_other is not None
        }
        self._adjusting = {
            str(tx.adjusts_other): tx
            for tx in self._user_transactions
            if tx.adjusts_other is not None
        }

    async def get_checkpoint(self, wallet_id):
        return self._checkpoints.get(str(wallet_id))

    async def get_unsettled_transactions(self, wallet_id, settled_at=None):
        return self._unsettled.get(str(wallet_id), [])

    async def get_user_transactions(self, user_id: int) -> list[TransactionEntity]:
        return list(self._user_transactions)

    async def get_user_transaction_by_id(self, user_id: int, transaction_id) -> TransactionEntity:
        transaction = self._by_id.get(str(transaction_id))
        if transaction is None:
            raise ValueError(f"transaction {transaction_id} not found")
        return transaction

    async def get_cancelling_transaction(self, transaction_id) -> TransactionEntity | None:
        return self._cancelling.get(str(transaction_id))

    async def get_adjusting_transaction(self, transaction_id) -> TransactionEntity | None:
        return self._adjusting.get(str(transaction_id))
