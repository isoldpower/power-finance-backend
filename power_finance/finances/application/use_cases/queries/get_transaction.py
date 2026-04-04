from dataclasses import dataclass
from uuid import UUID

from ...bootstrap import get_repository_registry
from ...dto_builders import transaction_to_dto
from ...dtos import TransactionDTO
from ...interfaces import TransactionRepository, WalletRepository


@dataclass(frozen=True)
class GetTransactionQuery:
    user_id: int
    transaction_id: str


class GetTransactionQueryHandler:
    transaction_repository: TransactionRepository
    wallet_repository: WalletRepository

    def __init__(
        self,
        transaction_repository: TransactionRepository | None = None,
        wallet_repository: WalletRepository | None = None
    ):
        registry = get_repository_registry()
        self.transaction_repository = transaction_repository or registry.transaction_repository
        self.wallet_repository = wallet_repository or registry.wallet_repository

    def handle(self, query: GetTransactionQuery) -> TransactionDTO:
        requested_transaction = self.transaction_repository.get_user_transaction_by_id(
            query.user_id,
            UUID(query.transaction_id)
        )

        sender_wallet = self.wallet_repository.get_user_wallet_by_id(
            requested_transaction.sender.wallet_id,
            query.user_id,
        ) if requested_transaction.sender else None
        receiver_wallet = self.wallet_repository.get_user_wallet_by_id(
            requested_transaction.receiver.wallet_id,
            query.user_id,
        ) if requested_transaction.receiver else None

        return transaction_to_dto(
            requested_transaction,
            sender_wallet,
            receiver_wallet
        )