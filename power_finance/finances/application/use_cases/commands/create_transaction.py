from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist
from django.core.management import CommandError

from finances.domain.services import apply_transaction_to_wallet_balance
from finances.domain.value_objects import Money
from finances.domain.entities import (
    Transaction,
    TransactionType,
    ExpenseCategory,
    Wallet, TransactionParticipant
)

from ..decorators import atomic_evently_command
from ..use_case_base import UseCaseEvently
from ...bootstrap import get_repository_registry
from ...dtos import TransactionDTO, CreateTransactionParticipantDTO
from ...dto_builders import transaction_to_dto
from ...interfaces import TransactionRepository, WalletRepository


@dataclass(frozen=True)
class CreateTransactionCommand:
    user_id: int
    sender: Optional[CreateTransactionParticipantDTO]
    receiver: Optional[CreateTransactionParticipantDTO]
    description: Optional[str]
    type: TransactionType
    category: Optional[ExpenseCategory]


class CreateTransactionCommandHandler(UseCaseEvently):
    _transaction_repository: TransactionRepository
    _wallet_repository: WalletRepository

    def __init__(
        self,
        transaction_repository: TransactionRepository | None = None,
        wallet_repository: WalletRepository | None = None,
    ):
        super().__init__()
        registry = get_repository_registry()

        self._transaction_repository = transaction_repository or registry.transaction_repository
        self._wallet_repository = wallet_repository or registry.wallet_repository

    async def _safe_get_wallet(self, wallet_id: UUID, user_id: int) -> Wallet | None:
        try:
            return await self._wallet_repository.get_user_wallet_for_update(
                wallet_id,
                user_id,
            )
        except ObjectDoesNotExist:
            return None

    async def _load_affected_wallets(
            self,
            sender: Optional[CreateTransactionParticipantDTO],
            receiver: Optional[CreateTransactionParticipantDTO],
            user_id: int,
    ) -> tuple[Wallet | None, Wallet | None]:
        sender_wallet = (
            await self._safe_get_wallet(sender.wallet_id, user_id) if sender else None
        )
        receiver_wallet = (
            await self._safe_get_wallet(receiver.wallet_id, user_id) if receiver else None
        )

        if (sender and not sender_wallet) or (receiver and not receiver_wallet):
            raise CommandError('One or more wallet IDs passed are invalid.')

        return sender_wallet, receiver_wallet

    async def _persist_wallets(self, *wallets: Wallet | None) -> None:
        for wallet in wallets:
            if wallet is not None:
                await self._wallet_repository.save_wallet(wallet)

    @atomic_evently_command()
    async def handle(self, command: CreateTransactionCommand) -> TransactionDTO:
        sender_wallet, receiver_wallet = await self._load_affected_wallets(
            command.sender,
            command.receiver,
            command.user_id,
        )

        new_transaction = Transaction.create(
            sender=TransactionParticipant(
                wallet_id=sender_wallet.id,
                money=Money(
                    amount=command.sender.amount,
                    currency_code=sender_wallet.balance.currency_code,
                )
            ) if (sender_wallet and command.sender) else None,
            receiver=TransactionParticipant(
                wallet_id=receiver_wallet.id,
                money=Money(
                    amount=command.receiver.amount,
                    currency_code=receiver_wallet.balance.currency_code,
                )
            ) if (receiver_wallet and command.receiver) else None,
            description=command.description,
            type=command.type,
            category=command.category,
            event_collector=self.event_collector,
        )

        apply_transaction_to_wallet_balance(new_transaction, sender_wallet, receiver_wallet)
        created_transaction = await self._transaction_repository.create_transaction(new_transaction)
        await self._persist_wallets(sender_wallet, receiver_wallet)

        return transaction_to_dto(
            created_transaction,
            sender_wallet,
            receiver_wallet,
        )