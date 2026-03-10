from uuid import UUID

from finances.application.interfaces.transaction_repository import TransactionRepository
from finances.domain.entities.transaction import Transaction
from finances.infrastructure.mappers.transaction_mapper import TransactionMapper
from finances.infrastructure.orm.transaction import TransactionModel


class DjangoTransactionRepository(TransactionRepository):
    def get_user_transactions(self, user_id: UUID) -> list[Transaction]:
        models = TransactionModel.objects.filter(user_id=user_id).order_by("created_at", "id")
        return [TransactionMapper.to_domain(model) for model in models]
