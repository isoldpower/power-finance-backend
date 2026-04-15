from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q, QuerySet

from finances.application.interfaces import TransactionRepository
from finances.domain.entities import Transaction, ResolvedFilterTree

from ..mappers import TransactionMapper
from ..orm import TransactionModel


class DjangoTransactionRepository(TransactionRepository):
    async def get_user_transactions(self, user_id: int) -> list[Transaction]:
        queryset: QuerySet[TransactionModel] = (TransactionModel.objects
            .select_related("send_wallet__currency", "receive_wallet__currency")
            .filter(Q(send_wallet__user_id=user_id) | Q(receive_wallet__user_id=user_id))
            .order_by("created_at", "id"))

        return [TransactionMapper.to_domain(model) async for model in queryset]

    async def get_user_transaction_by_id(self, user_id: int, transaction_id: UUID) -> Transaction:
        requested_transaction: TransactionModel = await (TransactionModel.objects
            .select_related("send_wallet__currency", "receive_wallet__currency")
            .filter(id=transaction_id)
            .aget(Q(send_wallet__user_id=user_id) | Q(receive_wallet__user_id=user_id)))

        return TransactionMapper.to_domain(requested_transaction)

    async def create_transaction(self, transaction: Transaction) -> Transaction:
        created_transaction: TransactionModel = TransactionModel()

        TransactionMapper.update_model(created_transaction, transaction)
        await created_transaction.asave()

        return TransactionMapper.to_domain(created_transaction)

    async def save_transaction(self, transaction: Transaction) -> Transaction:
        requested_transaction: TransactionModel = await TransactionModel.objects.aget(id=transaction.id)
        modified_fields = TransactionMapper.get_changed_fields(requested_transaction, transaction)

        TransactionMapper.update_model(requested_transaction, transaction)
        await requested_transaction.asave(update_fields=modified_fields)

        return TransactionMapper.to_domain(requested_transaction)

    async def delete_transaction_by_id(self, transaction_id: UUID) -> Transaction:
        requested_transaction: TransactionModel = await TransactionModel.objects.aget(id=transaction_id)
        domain_transaction: Transaction = TransactionMapper.to_domain(requested_transaction)

        deleted_count, deleted_transaction = await requested_transaction.adelete()
        if deleted_count == 0:
            raise ObjectDoesNotExist("Transaction with specified ID does not exist.")
        return domain_transaction

    async def list_transactions_with_filters(self, tree: ResolvedFilterTree, user_id: int) -> list[Transaction]:
        filtered_transactions = (TransactionModel.objects
            .select_related("send_wallet__currency", "receive_wallet__currency")
            .filter(
                (Q(send_wallet__user_id=user_id) | Q(receive_wallet__user_id=user_id))
                & tree.query
            )
            .distinct())

        return [TransactionMapper.to_domain(transaction) async for transaction in filtered_transactions]

