from dataclasses import dataclass
from uuid import UUID
from django.core.exceptions import ObjectDoesNotExist

from finances.domain.entities import Transaction, Wallet
from finances.domain.services import rollback_transaction_from_wallet_balance

from ..use_case_base import UseCaseEvently
from ..decorators import atomic_evently_command
from ...bootstrap import get_repository_registry
from ...dto_builders import transaction_to_dto
from ...dtos import TransactionDTO
from ...interfaces import TransactionRepository, WalletRepository


@dataclass(frozen=True)
class DeleteTransactionCommand:
    transaction_id: str
    user_id: int


class DeleteTransactionCommandHandler(UseCaseEvently):
    transaction_repository: TransactionRepository
    wallet_repository: WalletRepository

    def __init__(
        self,
        transaction_repository: TransactionRepository | None = None,
        wallet_repository: WalletRepository | None = None
    ):
        super().__init__()
        registry = get_repository_registry()

        self.transaction_repository = transaction_repository or registry.transaction_repository
        self.wallet_repository = wallet_repository or registry.wallet_repository

    def _safe_get_wallet(self, wallet_id: UUID, user_id: int) -> Wallet | None:
        try:
            return self.wallet_repository.get_user_wallet_for_update(
                wallet_id,
                user_id,
            )
        except ObjectDoesNotExist:
            return None

    def _load_affected_wallets(
        self,
        cancelled_transaction: Transaction,
        user_id: int,
    ) -> tuple[Wallet | None, Wallet | None]:
        sender_wallet = (
            self._safe_get_wallet(cancelled_transaction.sender.wallet_id, user_id)
            if cancelled_transaction.sender else None
        )
        receiver_wallet = (
            self._safe_get_wallet(cancelled_transaction.receiver.wallet_id, user_id)
            if cancelled_transaction.receiver else None
        )

        return sender_wallet, receiver_wallet

    def _persist_wallets(self, *wallets: Wallet | None) -> None:
        for wallet in wallets:
            if wallet is not None:
                self.wallet_repository.save_wallet(wallet)

    @atomic_evently_command()
    def handle(self, command: DeleteTransactionCommand) -> TransactionDTO:
        transaction_uuid = UUID(command.transaction_id)
        transaction_to_delete = self.transaction_repository.get_user_transaction_by_id(
            user_id=command.user_id,
            transaction_id=transaction_uuid,
        )
        transaction_to_delete.migrate_event_collector(self.event_collector)
        participants = self._load_affected_wallets(transaction_to_delete, command.user_id)

        rollback_transaction_from_wallet_balance(transaction_to_delete, *participants)
        self._persist_wallets(*participants)
        transaction_to_delete.confirm_delete()

        deleted_transaction = self.transaction_repository.delete_transaction_by_id(transaction_uuid)

        return transaction_to_dto(deleted_transaction, *participants)
