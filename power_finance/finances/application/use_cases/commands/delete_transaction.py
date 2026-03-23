from dataclasses import dataclass
from uuid import UUID
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from finances.infrastructure.repositories import DjangoTransactionRepository, DjangoWalletRepository
from finances.domain.entities import Transaction, Wallet
from finances.domain.services import rollback_transaction_from_wallet_balance

from ...dto_builders import transaction_to_dto
from ...dtos import TransactionDTO
from ...interfaces import TransactionRepository, WalletRepository


@dataclass(frozen=True)
class DeleteTransactionCommand:
    transaction_id: str
    user_id: int


class DeleteTransactionCommandHandler:
    transaction_repository: TransactionRepository
    wallet_repository: WalletRepository

    def __init__(
        self,
        transaction_repository: TransactionRepository | None = None,
        wallet_repository: WalletRepository | None = None
    ):
        self.transaction_repository = transaction_repository or DjangoTransactionRepository()
        self.wallet_repository = wallet_repository or DjangoWalletRepository()

    def _safe_get_wallet(self, wallet_id: UUID, user_id: int) -> Wallet | None:
        try:
            return self.wallet_repository.get_user_wallet_for_update(
                wallet_id,
                user_id,
            )
        except ObjectDoesNotExist:
            return None

    def _rollback_wallet_balances(self, deleted_transaction: Transaction, user_id: int):
        participants: list[Wallet | None] = [
            self._safe_get_wallet(deleted_transaction.sender.wallet_id, user_id)
                if deleted_transaction.sender else None,
            self._safe_get_wallet(deleted_transaction.receiver.wallet_id, user_id)
                if deleted_transaction.receiver else None,
        ]

        rollback_transaction_from_wallet_balance(
            deleted_transaction,
            participants[0],
            participants[1],
        )

        for participant in [participant for participant in participants if participant is not None]:
            self.wallet_repository.save_wallet(participant)

    @transaction.atomic
    def handle(self, command: DeleteTransactionCommand) -> TransactionDTO:
        transaction_to_delete = self.transaction_repository.get_user_transaction_by_id(
            user_id=command.user_id,
            transaction_id=UUID(command.transaction_id),
        )
        self._rollback_wallet_balances(transaction_to_delete, command.user_id)

        deleted_transaction = self.transaction_repository.delete_transaction_by_id(
            UUID(command.transaction_id),
        )
        sender_wallet = self._safe_get_wallet(deleted_transaction.sender.wallet_id, command.user_id)
        receiver_wallet = self._safe_get_wallet(deleted_transaction.receiver.wallet_id, command.user_id)

        return transaction_to_dto(
            deleted_transaction,
            sender_wallet,
            receiver_wallet
        )
