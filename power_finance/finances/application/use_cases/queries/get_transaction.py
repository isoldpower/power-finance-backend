from dataclasses import dataclass
from uuid import UUID

from ...dto_builders import transaction_to_dto
from ...dtos import TransactionDTO
from ...interfaces import TransactionRepository, WalletRepository

from finances.infrastructure.repositories import DjangoTransactionRepository
from finances.infrastructure.repositories import DjangoWalletRepository


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
        self.transaction_repository = transaction_repository or DjangoTransactionRepository()
        self.wallet_repository = wallet_repository or DjangoWalletRepository()

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