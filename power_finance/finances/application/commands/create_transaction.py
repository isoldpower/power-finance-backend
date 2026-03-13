from dataclasses import dataclass
from typing import Optional
from uuid import uuid4
from django.db import transaction
from django.utils import timezone

from finances.infrastructure.repositories import DjangoTransactionRepository, DjangoWalletRepository
from finances.domain.entities import Transaction, TransactionParticipant, TransactionType, ExpenseCategory, Wallet
from finances.domain.services import apply_transaction_to_wallet_balance

from ..dtos import TransactionDTO, TransactionParticipantPlainDTO
from ..dto_builders import transaction_to_dto
from ..interfaces import TransactionRepository, WalletRepository


@dataclass(frozen=True)
class CreateTransactionCommand:
    user_id: int
    sender: Optional[TransactionParticipantPlainDTO]
    receiver: Optional[TransactionParticipantPlainDTO]
    description: Optional[str]
    type: TransactionType
    category: Optional[ExpenseCategory]


class CreateTransactionCommandHandler:
    transaction_repository: TransactionRepository
    wallet_repository: WalletRepository

    def __init__(
        self,
        transaction_repository: TransactionRepository | None = None,
        wallet_repository: WalletRepository | None = None,
    ):
        self.transaction_repository = transaction_repository or DjangoTransactionRepository()
        self.wallet_repository = wallet_repository or DjangoWalletRepository()

    def _update_wallet_balances(self, new_transaction: Transaction, user_id: int):
        participants: list[Wallet | None] = [
            self.wallet_repository.get_user_wallet_for_update(
                new_transaction.sender.wallet_id,
                user_id,
            ) if new_transaction.sender else None,
            self.wallet_repository.get_user_wallet_for_update(
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
            self.wallet_repository.save_wallet(participant)

    @transaction.atomic
    def handle(self, command: CreateTransactionCommand) -> TransactionDTO:
        new_transaction = Transaction(
            id=uuid4(),
            sender=TransactionParticipant(
                wallet_id=command.sender.wallet_id,
                amount=command.sender.amount,
            ) if command.sender else None,
            receiver=TransactionParticipant(
                wallet_id=command.receiver.wallet_id,
                amount=command.receiver.amount,
            ) if command.receiver else None,
            description=command.description,
            created_at=timezone.now(),
            type=command.type,
            category=command.category
        )

        self._update_wallet_balances(new_transaction, command.user_id)

        created_transaction = self.transaction_repository.create_transaction(new_transaction)
        sender_wallet = self.wallet_repository.get_user_wallet_by_id(
            created_transaction.sender.wallet_id,
            command.user_id,
        ) if created_transaction.sender else None
        receiver_wallet = self.wallet_repository.get_user_wallet_by_id(
            created_transaction.receiver.wallet_id,
            command.user_id,
        ) if created_transaction.receiver else None

        return transaction_to_dto(
            created_transaction,
            sender_wallet,
            receiver_wallet,
        )
