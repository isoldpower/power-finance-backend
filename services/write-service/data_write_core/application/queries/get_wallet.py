from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from write_service.common.timestamps import DEFAULT_PERIOD, Period, period_bounds

from data_write_core.domain.services import reconstruct_balance

from ..bootstrap import get_repository_registry
from ..dtos import WalletDTO, wallet_to_dto
from ..interfaces import MoneyFlowRepository, WalletRepository
from ._wallet_balance import load_balance_inputs


@dataclass(frozen=True)
class GetFallbackWalletQuery:
    user_id: int
    wallet_id: UUID
    zone: ZoneInfo
    period: Period = DEFAULT_PERIOD


@dataclass(frozen=True)
class FallbackWalletDetail:
    wallet: WalletDTO
    inflow: Decimal
    outflow: Decimal


class GetFallbackWalletQueryHandler:
    def __init__(
        self,
        wallet_repository: WalletRepository | None = None,
        money_flow_repository: MoneyFlowRepository | None = None,
    ) -> None:
        if wallet_repository is None or money_flow_repository is None:
            registry = get_repository_registry()
            wallet_repository = wallet_repository or registry.wallet_repository
            money_flow_repository = money_flow_repository or registry.money_flow_repository

        self._wallet_repository = wallet_repository
        self._transaction_repository = money_flow_repository

    async def handle(self, query: GetFallbackWalletQuery) -> FallbackWalletDetail:
        wallet = await self._wallet_repository.get_user_wallet_by_id(
            wallet_id=query.wallet_id,
            user_id=query.user_id,
        )

        checkpoint, unsettled = await load_balance_inputs(wallet, self._transaction_repository)
        balance = reconstruct_balance(wallet, checkpoint, unsettled)
        inflow, outflow = await self._period_flows(query)

        return FallbackWalletDetail(
            wallet=wallet_to_dto(wallet, balance_amount=balance),
            inflow=inflow,
            outflow=outflow,
        )

    async def _period_flows(self, query: GetFallbackWalletQuery) -> tuple[Decimal, Decimal]:
        since, until = period_bounds(query.period, query.zone)
        entries = await self._transaction_repository.get_wallet_flows_between(
            wallet_id=query.wallet_id,
            since=since,
            until=until,
        )

        inflow = sum((entry.amount for entry in entries if entry.amount > 0), Decimal("0"))
        outflow = sum((entry.amount for entry in entries if entry.amount < 0), Decimal("0"))

        return inflow, -outflow
