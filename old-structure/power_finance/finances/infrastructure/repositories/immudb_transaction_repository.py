from decimal import Decimal
from uuid import UUID

from django.utils import timezone
from immudb.constants import COLUMN_NAME_MODE_FIELD
from immudb.datatypesv2 import PrimaryKeyVarCharValue

from finances.application.bootstrap.state import ImmudbConnection
from finances.application.interfaces import TransactionRepository
from finances.domain.entities import BalanceCheckpoint, ResolvedFilterTree, Transaction
from finances.infrastructure.mappers import TransactionMapper


class ImmudbTransactionRepository(TransactionRepository):
    def __init__(self, immudb_client: ImmudbConnection):
        self._immudb = immudb_client.client
        self._token = immudb_client.transaction_token
        self._transactions_table = 'transactions'
        self._checkpoints_table = 'balance_checkpoints'

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

    async def get_unsettled_transactions(self, wallet_id: UUID, settled_at: str | None = None) -> list[Transaction]:
        if settled_at is not None:
            results = self._immudb.sqlQuery(
                f'SELECT * FROM {self._transactions_table} WHERE source_wallet_id = @wallet_id AND created_at > @settled_at;',
                {'wallet_id': str(wallet_id), 'settled_at': settled_at},
                COLUMN_NAME_MODE_FIELD,
            )
        else:
            results = self._immudb.sqlQuery(
                f'SELECT * FROM {self._transactions_table} WHERE source_wallet_id = @wallet_id;',
                {'wallet_id': str(wallet_id)},
                COLUMN_NAME_MODE_FIELD,
            )

        verified = []
        for transaction in results:
            self._immudb.verifiableSQLGet(
                self._transactions_table,
                [PrimaryKeyVarCharValue(value=transaction.get('id'))],
            )
            verified.append(transaction)

        return [TransactionMapper.to_domain(t) for t in verified]

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
            {'user_id': user_id, **tree.raw_sql_params},
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

    async def get_checkpoint(self, wallet_id: UUID) -> BalanceCheckpoint | None:
        results = self._immudb.sqlQuery(
            f'SELECT * FROM {self._checkpoints_table} WHERE wallet_id = @wallet_id;',
            {'wallet_id': str(wallet_id)},
            COLUMN_NAME_MODE_FIELD,
        )
        rows = list(results)
        if not rows:
            return None
        row = rows[0]
        return BalanceCheckpoint(
            wallet_id=UUID(row['wallet_id']),
            balance=Decimal(row['balance']),
            currency=row['currency'],
            settled_at=row['settled_at'],
            last_tx_id=UUID(row['last_tx_id']) if row.get('last_tx_id') else None,
        )

    async def save_checkpoint(self, checkpoint: BalanceCheckpoint) -> None:
        self._immudb.sqlExec(
            f'UPSERT INTO {self._checkpoints_table} (wallet_id, balance, currency, settled_at, last_tx_id) '
            f'VALUES (@wallet_id, @balance, @currency, @settled_at, @last_tx_id);',
            {
                'wallet_id': str(checkpoint.wallet_id),
                'balance': str(checkpoint.balance),
                'currency': checkpoint.currency,
                'settled_at': checkpoint.settled_at,
                'last_tx_id': str(checkpoint.last_tx_id) if checkpoint.last_tx_id else None,
            },
        )
