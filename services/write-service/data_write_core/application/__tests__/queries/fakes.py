from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from write_service.common.pagination import (
    CREATED_AT_DESC,
    PageRequest,
    keyset_slice,
    query_fingerprint,
)

from data_write_core.domain.entities import (
    BalanceCheckpointEntity,
    MoneyFlowEntity,
    TransactionEntity,
    WalletEntity,
)
from data_write_core.domain.events import EventCollector
from data_write_core.domain.value_objects import (
    MoneyFlowData,
    TransactionMetadata,
    TransactionOrigin,
    WalletData,
)


@dataclass(frozen=True)
class _KeyedRow:
    id: str
    created_at: datetime
    wallet: WalletEntity


def make_page(limit: int = 25, cursor=None) -> PageRequest:
    """A PageRequest as the view layer would have built it."""

    return PageRequest(
        limit=limit,
        order=CREATED_AT_DESC,
        fingerprint=query_fingerprint(CREATED_AT_DESC),
        cursor=cursor,
    )


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


def make_flow(
    flow_id: str,
    wallet_id: str,
    amount: str,
    *,
    transaction_id: str | None = None,
    user_id: int = 7,
    created_at: datetime | None = None,
    cancels_other: UUID | None = None,
    adjusts_other: UUID | None = None,
) -> MoneyFlowEntity:
    """A ledger row. `transaction_id` defaults to the flow's own id, which is
    what a transaction's opening flow looks like before anything corrects it."""

    return MoneyFlowEntity.from_persistence(
        id=UUID(flow_id),
        user_id=user_id,
        created_at=created_at or datetime(2026, 1, 1),
        data=MoneyFlowData(
            transaction_id=UUID(transaction_id or flow_id),
            source_wallet_id=UUID(wallet_id),
            amount=Decimal(amount),
            cancels_other=cancels_other,
            adjusts_other=adjusts_other,
        ),
    )


def make_transaction_entity(
    transaction_id: str,
    wallet_id: str,
    *,
    user_id: int = 7,
    name: str = "Groceries",
    category: str | None = None,
    origin: TransactionOrigin = TransactionOrigin.MANUAL,
    chain_id: UUID | None = None,
    created_at: datetime | None = None,
    deleted_at: datetime | None = None,
) -> TransactionEntity:
    return TransactionEntity(
        id=UUID(transaction_id),
        user_id=str(user_id),
        wallet_id=UUID(wallet_id),
        metadata=TransactionMetadata(
            name=name,
            category=category,
            origin=origin,
            chain_id=chain_id,
        ),
        created_at=created_at or datetime(2026, 1, 1),
        deleted_at=deleted_at,
        event_collector=EventCollector(),
    )


class FakeTransactionRepository:
    """The Postgres half — the mutable transaction rows."""

    def __init__(self, transactions: list[TransactionEntity] | None = None) -> None:
        self._transactions = {
            str(transaction.unique_id): transaction for transaction in (transactions or [])
        }
        self.chains: dict[str, dict] = {}

    async def create_transaction(self, transaction: TransactionEntity) -> TransactionEntity:
        self._transactions[str(transaction.unique_id)] = transaction
        return transaction

    async def save_transaction(self, transaction: TransactionEntity) -> TransactionEntity:
        self._transactions[str(transaction.unique_id)] = transaction
        return transaction

    async def get_user_transaction_by_id(self, transaction_id, user_id: int) -> TransactionEntity:
        transaction = self._transactions.get(str(transaction_id))
        if transaction is None:
            raise ValueError(f"transaction {transaction_id} not found")
        return transaction

    async def get_user_transactions(self, user_id: int, page=None) -> list[TransactionEntity]:
        live = [
            transaction
            for transaction in self._transactions.values()
            if transaction.deleted_at is None
        ]
        ordered = sorted(
            live,
            key=lambda transaction: (transaction.created_at, transaction.unique_id),
            reverse=True,
        )
        if page is None:
            return ordered

        rows = [
            _KeyedRow(
                id=transaction.unique_id, created_at=transaction.created_at, wallet=transaction
            )
            for transaction in ordered
        ]
        return [row.wallet for row in keyset_slice(rows, page)]

    async def count_user_transactions(self, user_id: int) -> int:
        return len(
            [
                transaction
                for transaction in self._transactions.values()
                if transaction.deleted_at is None
            ]
        )

    async def hard_delete_transaction(self, transaction_id) -> None:
        self._transactions.pop(str(transaction_id), None)

    async def create_chain(self, chain_id, user_id: int, created_at) -> None:
        self.chains[str(chain_id)] = {"user_id": user_id, "created_at": created_at}

    async def get_chain_transactions(self, chain_id, user_id: int) -> list[TransactionEntity]:
        return [
            transaction
            for transaction in self._transactions.values()
            if transaction.chain_id == chain_id
        ]

    async def hard_delete_chain(self, chain_id) -> None:
        self.chains.pop(str(chain_id), None)
        for key, transaction in list(self._transactions.items()):
            if transaction.chain_id == chain_id:
                del self._transactions[key]


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
        self, user_id: int, page: PageRequest | None = None
    ) -> list[WalletEntity]:
        ordered = sorted(
            self._wallets.values(),
            key=lambda wallet: wallet.created_at,
            reverse=True,
        )
        if page is None:
            return ordered

        rows = [
            _KeyedRow(id=wallet.unique_id, created_at=wallet.created_at, wallet=wallet)
            for wallet in ordered
        ]

        return [row.wallet for row in keyset_slice(rows, page)]

    async def count_user_wallets(self, user_id: int) -> int:
        return len(self._wallets)


class FakeMoneyFlowRepository:
    def __init__(
        self,
        *,
        checkpoints: dict[str, BalanceCheckpointEntity] | None = None,
        unsettled: dict[str, list[MoneyFlowEntity]] | None = None,
        user_transactions: list[MoneyFlowEntity] | None = None,
    ) -> None:
        self._checkpoints = checkpoints or {}
        self._unsettled = unsettled or {}
        self._user_transactions = user_transactions or []
        self._by_id = {
            str(transaction.unique_id): transaction for transaction in self._user_transactions
        }
        self._cancelling = {
            str(transaction.cancels_other): transaction
            for transaction in self._user_transactions
            if transaction.cancels_other is not None
        }
        self._adjusting = {
            str(transaction.adjusts_other): transaction
            for transaction in self._user_transactions
            if transaction.adjusts_other is not None
        }

    async def get_checkpoint(self, wallet_id):
        return self._checkpoints.get(str(wallet_id))

    async def get_unsettled_flows(self, wallet_id, settled_at=None):
        return self._unsettled.get(str(wallet_id), [])

    async def get_flows_for_transaction(self, transaction_id):
        return [
            flow
            for flows in self._unsettled.values()
            for flow in flows
            if flow.transaction_id == transaction_id
        ] or [flow for flow in self._user_transactions if flow.transaction_id == transaction_id]

    async def get_flows_for_transactions(self, transaction_ids):
        return {
            transaction_id: await self.get_flows_for_transaction(transaction_id)
            for transaction_id in transaction_ids
        }

    async def get_wallet_flows_between(self, wallet_id, since, until):
        return [
            transaction
            for transaction in self._unsettled.get(str(wallet_id), [])
            if since <= _aware(transaction.created_at) < until
        ]

    async def get_user_flows(self, user_id: int) -> list[MoneyFlowEntity]:
        return list(self._user_transactions)

    async def get_user_flow_by_id(self, user_id: int, transaction_id) -> MoneyFlowEntity:
        transaction = self._by_id.get(str(transaction_id))
        if transaction is None:
            raise ValueError(f"transaction {transaction_id} not found")
        return transaction

    async def get_cancelling_flow(self, transaction_id) -> MoneyFlowEntity | None:
        return self._cancelling.get(str(transaction_id))

    async def get_adjusting_flow(self, transaction_id) -> MoneyFlowEntity | None:
        return self._adjusting.get(str(transaction_id))


def _aware(moment):
    """Fixture transactions are built with naive datetimes; the window the
    handler asks for is UTC-aware."""

    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)
