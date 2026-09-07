from decimal import Decimal
from typing import Any
from uuid import UUID

from data_write_core.application.commands.config import TransferLeg
from data_write_core.domain.automations import RunContext
from data_write_core.domain.value_objects import (
    TransactionOrigin,
    TransactionType,
)

from .....interfaces import EffectExecutor
from ....transaction_chains.create_transaction_chain import (
    ChainEntryCommand,
    CreateTransactionChainCommand,
    CreateTransactionChainCommandHandler,
)


class TransferEffect(EffectExecutor):
    async def apply(self, params: dict[str, Any], context: RunContext) -> None:
        money = params["money"]
        amount = Decimal(str(money["amount"]))
        name = f"Transfer — {context.automation_name}"

        await CreateTransactionChainCommandHandler().handle(
            CreateTransactionChainCommand(
                user_id=context.user_id,
                user_external_id=context.user_external_id,
                entries=[
                    ChainEntryCommand(
                        temporary_id=TransferLeg.WITHDRAWAL,
                        wallet_id=UUID(str(params["from_wallet_id"])),
                        amount=amount,
                        name=name,
                        transaction_type=TransactionType.EXPENSE,
                        origin=TransactionOrigin.AUTOMATION,
                    ),
                    ChainEntryCommand(
                        temporary_id=TransferLeg.DEPOSIT,
                        after=TransferLeg.WITHDRAWAL,
                        wallet_id=UUID(str(params["to_wallet_id"])),
                        amount=amount,
                        name=name,
                        transaction_type=TransactionType.INCOME,
                        origin=TransactionOrigin.AUTOMATION,
                    ),
                ],
            )
        )
