from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q, QuerySet

from finances.application.interfaces import TransactionRepository
from finances.domain.entities import Transaction

from ..mappers import TransactionMapper
from ..orm import TransactionModel


class DjangoTransactionRepository(TransactionRepository):
    def get_user_transactions(self, user_id: int) -> list[Transaction]:
        queryset: QuerySet[TransactionModel] = (TransactionModel.objects
            .filter(Q(send_wallet__user_id=user_id) | Q(receive_wallet__user_id=user_id))
            .order_by("created_at", "id"))

        return [TransactionMapper.to_domain(model) for model in queryset]

    def get_user_transaction_by_id(self, user_id: int, transaction_id: UUID) -> Transaction:
        requested_transaction: TransactionModel = (TransactionModel.objects
            .filter(id=transaction_id)
            .get(Q(send_wallet__user_id=user_id) | Q(receive_wallet__user_id=user_id)))

        return TransactionMapper.to_domain(requested_transaction)

    def create_transaction(self, transaction: Transaction) -> Transaction:
        created_transaction: TransactionModel = TransactionModel()

        TransactionMapper.update_model(created_transaction, transaction)
        created_transaction.save()

        return TransactionMapper.to_domain(created_transaction)

    def save_transaction(self, transaction: Transaction) -> Transaction:
        requested_transaction: TransactionModel = TransactionModel.objects.get(id=transaction.id)
        modified_fields = TransactionMapper.get_changed_fields(requested_transaction, transaction)

        TransactionMapper.update_model(requested_transaction, transaction)

        requested_transaction.save(update_fields=modified_fields)
        return TransactionMapper.to_domain(requested_transaction)

    def delete_transaction_by_id(self, transaction_id: UUID) -> Transaction:
        requested_transaction: TransactionModel = TransactionModel.objects.get(id=transaction_id)
        domain_transaction: Transaction = TransactionMapper.to_domain(requested_transaction)

        deleted_count, deleted_transaction = requested_transaction.delete()
        if deleted_count == 0:
            raise ObjectDoesNotExist("Transaction with specified ID does not exist.")
        return domain_transaction
