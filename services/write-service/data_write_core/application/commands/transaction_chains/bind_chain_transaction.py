from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ..transactions.transaction_saga import run_transaction_saga
from ._chain_members import bind_member_step, chain_joined_entry, load_bound_member
from ._chain_membership_base import ChainMembershipCommandHandlerBase


@dataclass(frozen=True)
class BindChainTransactionCommand:
    user_id: int
    user_external_id: str
    chain_id: UUID
    transaction_id: UUID


class BindChainTransactionCommandHandler(
    ChainMembershipCommandHandlerBase[BindChainTransactionCommand]
):
    async def _add_member(self, command: BindChainTransactionCommand) -> int:
        bound_at = datetime.now()
        bound_aggregate = await load_bound_member(
            self._transaction_repository,
            self._money_flow_repository,
            transaction_id=command.transaction_id,
            user_id=command.user_id,
            chain_id=command.chain_id,
            bound_at=bound_at,
        )

        write_version = await run_transaction_saga(
            postgres_steps=[bind_member_step(self._transaction_repository, bound_aggregate)],
            flows=[],
            entries=[chain_joined_entry(bound_aggregate, command.user_external_id, bound_at)],
            money_flow_repository=self._money_flow_repository,
            outbox_repository=self._outbox_repository,
        )
        await self._publish_domain_events(bound_aggregate)

        return write_version
