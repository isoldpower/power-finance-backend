from dataclasses import dataclass
from decimal import Decimal
from typing import Unpack
from uuid import UUID

from data_write_core.domain.value_objects import TransactionOrigin, TransactionType

from .._ledger_command_base import LedgerRepositoryOverrides
from ..transactions.create_transaction import (
    CreateTransactionCommand,
    CreateTransactionCommandHandler,
)
from ._chain_membership_base import ChainMembershipCommandHandlerBase


@dataclass(frozen=True)
class AttachChainTransactionCommand:
    user_id: int
    user_external_id: str
    chain_id: UUID
    wallet_id: UUID
    amount: Decimal
    name: str
    transaction_type: TransactionType
    origin: TransactionOrigin = TransactionOrigin.MANUAL
    category_id: UUID | None = None
    evidence_url: str | None = None


class AttachChainTransactionCommandHandler(
    ChainMembershipCommandHandlerBase[AttachChainTransactionCommand]
):
    def __init__(
        self,
        create_transaction_handler: CreateTransactionCommandHandler | None = None,
        **repositories: Unpack[LedgerRepositoryOverrides],
    ) -> None:
        super().__init__(**repositories)
        self._create_transaction_handler = create_transaction_handler or (
            CreateTransactionCommandHandler(**self._repositories._asdict())
        )

    async def _add_member(self, command: AttachChainTransactionCommand) -> int:
        _, write_version = await self._create_transaction_handler.handle(
            CreateTransactionCommand(
                user_id=command.user_id,
                user_external_id=command.user_external_id,
                wallet_id=command.wallet_id,
                amount=command.amount,
                name=command.name,
                transaction_type=command.transaction_type,
                origin=command.origin,
                category_id=command.category_id,
                evidence_url=command.evidence_url,
                chain_id=command.chain_id,
            )
        )

        return write_version
