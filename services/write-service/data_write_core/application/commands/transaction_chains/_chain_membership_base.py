from abc import abstractmethod
from typing import Protocol
from uuid import UUID

from data_write_core.domain.aggregates import TransactionAggregate
from data_write_core.domain.exceptions import TransactionChainNotFoundError
from data_write_core.domain.services import ensure_chain_accepts_member

from ...dtos import TransactionChainDTO, transaction_to_dto
from .._ledger_command_base import LedgerCommandHandlerBase
from .._loaded_containers import LoadedContainers


class ChainMembershipCommand(Protocol):
    @property
    def user_id(self) -> int: ...

    @property
    def chain_id(self) -> UUID: ...


class ChainMembershipCommandHandlerBase[CommandType: ChainMembershipCommand](
    LedgerCommandHandlerBase[TransactionChainDTO]
):
    async def handle(self, command: CommandType) -> tuple[TransactionChainDTO, int]:
        current_members = await self._transaction_repository.get_chain_transactions(
            chain_id=command.chain_id,
            user_id=command.user_id,
        )
        if not current_members:
            raise TransactionChainNotFoundError(command.chain_id)

        ensure_chain_accepts_member(command.chain_id, current_members)
        write_version = await self._add_member(command)

        return await self._present_chain(command), write_version

    @abstractmethod
    async def _add_member(self, command: CommandType) -> int:
        raise NotImplementedError()

    async def _present_chain(self, command: CommandType) -> TransactionChainDTO:
        grown_members = await self._transaction_repository.get_chain_transactions(
            chain_id=command.chain_id,
            user_id=command.user_id,
        )
        aggregates = [
            TransactionAggregate(
                transaction_entity=member,
                flows=await self._money_flow_repository.get_flows_for_transaction(
                    UUID(member.unique_id)
                ),
            )
            for member in grown_members
        ]
        containers = LoadedContainers(loader=self, user_id=command.user_id)
        for aggregate in aggregates:
            await containers.get(aggregate.root.container_id)
        container_dtos = containers.as_dtos()

        return TransactionChainDTO(
            chain_id=command.chain_id,
            transactions=[
                transaction_to_dto(aggregate, container_dtos[str(aggregate.root.container_id)])
                for aggregate in aggregates
            ],
        )
