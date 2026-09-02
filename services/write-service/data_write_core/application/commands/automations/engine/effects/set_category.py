from typing import Any

from data_write_core.domain.automations import RunContext

from .....interfaces import EffectExecutor
from ....transactions.patch_transaction import (
    PatchTransactionCommand,
    PatchTransactionCommandHandler,
)


class SetCategoryEffect(EffectExecutor):
    async def apply(self, params: dict[str, Any], context: RunContext) -> None:
        await PatchTransactionCommandHandler().handle(
            PatchTransactionCommand(
                user_id=context.user_id,
                user_external_id=context.user_external_id,
                transaction_id=context.subject_id,
                category=str(params["category"]),
            )
        )
