from dataclasses import dataclass
from typing import Optional

from django.db import transaction

from finances.domain.value_objects import Money
from finances.infrastructure.repositories import (
    DjangoTransactionRepository,
    DjangoWalletRepository
)
from finances.domain.entities import (
    Transaction,
    TransactionType,
    ExpenseCategory,
    Wallet, TransactionParticipant
)
from finances.domain.services import apply_transaction_to_wallet_balance

from ..decorators import handle_evently_command
from ..use_case_base import UseCaseEvently
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

        self._transaction_repository = transaction_repository or DjangoTransactionRepository()
        self._wallet_repository = wallet_repository or DjangoWalletRepository()

    def _update_wallet_balances(self, new_transaction: Transaction, user_id: int):
        participants: list[Wallet | None] = [
            self._wallet_repository.get_user_wallet_for_update(
                new_transaction.sender.wallet_id,
                user_id,
            ) if new_transaction.sender else None,
            self._wallet_repository.get_user_wallet_for_update(
                new_transaction.receiver.wallet_id,
                user_id,
            ) if new_transaction.receiver else None,
        ]

        apply_transaction_to_wallet_balance(
            new_transaction,
            participants[0],
            participants[1],
        )

        for participant in [participant for participant in participants if participant is not None]:
            self._wallet_repository.save_wallet(participant)

    @handle_evently_command
    @transaction.atomic
    def handle(self, command: CreateTransactionCommand) -> TransactionDTO:
        sender_wallet = self._wallet_repository.get_user_wallet_by_id(
            command.sender.wallet_id,
            command.user_id,
        ) if command.sender else None
        receiver_wallet = self._wallet_repository.get_user_wallet_by_id(
            command.receiver.wallet_id,
            command.user_id,
        ) if command.receiver else None

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

        self._update_wallet_balances(new_transaction, command.user_id)
        created_transaction = self._transaction_repository.create_transaction(new_transaction)

        return transaction_to_dto(
            created_transaction,
            sender_wallet,
            receiver_wallet,
        )