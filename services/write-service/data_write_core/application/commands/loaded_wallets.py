from typing import Protocol
from uuid import UUID

from data_write_core.domain.aggregates import WalletAggregate

from ..dtos import WalletDTO, wallet_to_dto


class WalletAggregateLoader(Protocol):
    async def load_wallet_aggregate(self, wallet_id: UUID, user_id: int) -> WalletAggregate: ...


class LoadedWallets:
    """The wallets one command touches, each fetched once however many times the
    command names it."""

    def __init__(self, loader: WalletAggregateLoader, user_id: int) -> None:
        self._loader = loader
        self._user_id = user_id
        self._aggregates: dict[str, WalletAggregate] = {}

    async def get(self, wallet_id: UUID) -> WalletAggregate:
        wallet_key = str(wallet_id)
        if wallet_key not in self._aggregates:
            self._aggregates[wallet_key] = await self._loader.load_wallet_aggregate(
                wallet_id=wallet_id,
                user_id=self._user_id,
            )

        return self._aggregates[wallet_key]

    def as_dtos(self) -> dict[str, WalletDTO]:
        return {
            wallet_key: wallet_to_dto(aggregate.root, balance_amount=aggregate.balance)
            for wallet_key, aggregate in self._aggregates.items()
        }
