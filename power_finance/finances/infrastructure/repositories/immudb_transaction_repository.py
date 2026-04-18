from uuid import UUID

from django.utils import timezone
from immudb.constants import COLUMN_NAME_MODE_FIELD
from immudb.datatypesv2 import PrimaryKeyVarCharValue

from finances.application.bootstrap.state import ImmudbConnection
from finances.application.interfaces import TransactionRepository
from finances.domain.entities import ResolvedFilterTree, Transaction
from finances.infrastructure.mappers import TransactionMapper


class ImmudbTransactionRepository(TransactionRepository):
    def __init__(self, immudb_client: ImmudbConnection):
        self._immudb = immudb_client.client
        self._token = immudb_client.transaction_token
        self._transactions_table = 'transactions'

    async def get_user_transactions(self, user_id: int) -> list[Transaction]:
        user_transactions = self._immudb.sqlQuery(
            f'SELECT * FROM {self._transactions_table} WHERE user_id = @user_id;',
            { 'user_id': user_id },
            COLUMN_NAME_MODE_FIELD
        )

        verified_transactions = []
        for transaction in user_transactions:
            self._immudb.verifiableSQLGet(
                self._transactions_table,
                [PrimaryKeyVarCharValue(value=transaction['id'])],
            )
            verified_transactions.append(transaction)

        return [TransactionMapper.to_domain(transaction) for transaction in verified_transactions]

    async def get_wallet_transactions(self, wallet_id: UUID) -> list[Transaction]:
        wallet_transactions = self._immudb.sqlQuery(
            f'SELECT * FROM {self._transactions_table} WHERE source_wallet_id = @wallet_id;',
            {'wallet_id': str(wallet_id)},
            COLUMN_NAME_MODE_FIELD,
        )

        verified_transactions = []
        for transaction in wallet_transactions:
            self._immudb.verifiableSQLGet(
                self._transactions_table,
                [PrimaryKeyVarCharValue(value=transaction.get('id'))],
            )
            verified_transactions.append(transaction)

        return [TransactionMapper.to_domain(transaction) for transaction in verified_transactions]

    async def get_user_transaction_by_id(self, user_id: int, transaction_id: UUID) -> Transaction:
        query_params = {
            'id': str(transaction_id),
            'user_id': user_id,
        }
        user_transactions = self._immudb.sqlQuery(
            f'SELECT * FROM {self._transactions_table} WHERE id = @id AND user_id = @user_id;',
            query_params,
            COLUMN_NAME_MODE_FIELD,
        )
        user_transactions_list = list(user_transactions)

        if len(user_transactions_list) == 0:
            raise ValueError(f'No transactions found with resource ID: {transaction_id}')
        transaction = user_transactions_list[0]
        self._immudb.verifiableSQLGet(
            self._transactions_table,
            [PrimaryKeyVarCharValue(value=transaction['id'])],
        )

        return TransactionMapper.to_domain(transaction)

    async def create_transaction(self, transaction: Transaction) -> Transaction:
        insert_params = {
            'id': str(transaction.id),
            'user_id': transaction.user_id,
            'source_wallet_id': str(transaction.source_wallet_id),
            'amount': str(transaction.amount),
            'created_at': timezone.now().isoformat(),
        }

        if transaction.cancels_other is not None:
            insert_params['cancels_other'] = str(transaction.cancels_other)
        if transaction.adjusts_other is not None:
            insert_params['adjusts_other'] = str(transaction.adjusts_other)

        sql_columns = ', '.join(insert_params.keys())
        sql_values = ', '.join(f'@{sql_column}' for sql_column in insert_params.keys())
        self._immudb.sqlExec(
            f"INSERT INTO {self._transactions_table} ({sql_columns}) VALUES ({sql_values});",
            insert_params
        )

        return transaction

    async def get_cancelling_transaction(self, transaction_id: UUID) -> Transaction | None:
        results = self._immudb.sqlQuery(
            f'SELECT * FROM {self._transactions_table} WHERE cancels_other = @transaction_id;',
            {'transaction_id': str(transaction_id)},
            COLUMN_NAME_MODE_FIELD,
        )
        results_list = list(results)
        if not results_list:
            return None
        return TransactionMapper.to_domain(results_list[0])

    async def delete_transaction_by_id(self, user_id: int, transaction_id: UUID) -> Transaction:
        existing_cancellation = await self.get_cancelling_transaction(transaction_id)
        if existing_cancellation is not None:
            raise ValueError(f'Transaction {transaction_id} has already been cancelled by {existing_cancellation.id}')

        related_transaction = await self.get_user_transaction_by_id(user_id, transaction_id)
        inverse_transaction = related_transaction.delete()

        return await self.create_transaction(inverse_transaction)

    async def list_transactions_with_filters(self, tree: ResolvedFilterTree, user_id: int) -> list[Transaction]:
        user_transactions = self._immudb.sqlQuery(
            f'SELECT * FROM {self._transactions_table} WHERE (user_id = @user_id AND {tree.raw_sql_query});',
            {'user_id': user_id},
            COLUMN_NAME_MODE_FIELD
        )

        verified_transactions = []
        for transaction in user_transactions:
            self._immudb.verifiableSQLGet(
                self._transactions_table,
                [PrimaryKeyVarCharValue(value=transaction['id'])],
            )
            verified_transactions.append(transaction)

        return [TransactionMapper.to_domain(transaction) for transaction in verified_transactions]