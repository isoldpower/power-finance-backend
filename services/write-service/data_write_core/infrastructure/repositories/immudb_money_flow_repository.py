from datetime import datetime
from decimal import Decimal
from uuid import UUID

from immudb.constants import COLUMN_NAME_MODE_FIELD
from immudb.datatypesv2 import PrimaryKeyVarCharValue

from data_write_core.application.bootstrap.state import ImmudbConnection
from data_write_core.application.interfaces import MoneyFlowRepository
from data_write_core.domain.entities import BalanceCheckpointEntity, MoneyFlowEntity

from .mappers import MoneyFlowMapper


class ImmudbMoneyFlowRepository(MoneyFlowRepository):
    _TRANSACTIONS_TABLE = "transactions"
    _CHECKPOINTS_TABLE = "balance_checkpoints"

    def __init__(self, immudb_client: ImmudbConnection) -> None:
        self._immudb = immudb_client.client
        self._token = immudb_client.transaction_token

    def _verify(self, rows: list[dict]) -> list[dict]:
        verified = []
        for row in rows:
            self._immudb.verifiableSQLGet(
                self._TRANSACTIONS_TABLE,
                [PrimaryKeyVarCharValue(value=row["id"])],
            )
            verified.append(row)

        return verified

    async def get_user_flows(self, user_id: int) -> list[MoneyFlowEntity]:
        rows = self._immudb.sqlQuery(
            f"SELECT * FROM {self._TRANSACTIONS_TABLE} WHERE user_id = @user_id;",
            {"user_id": user_id},
            COLUMN_NAME_MODE_FIELD,
        )

        return [MoneyFlowMapper.to_domain(row) for row in self._verify(list(rows))]

    async def get_user_flow_by_id(
        self,
        user_id: int,
        transaction_id: UUID,
    ) -> MoneyFlowEntity:
        rows = list(
            self._immudb.sqlQuery(
                f"SELECT * FROM {self._TRANSACTIONS_TABLE} WHERE id = @id AND user_id = @user_id;",
                {"id": str(transaction_id), "user_id": user_id},
                COLUMN_NAME_MODE_FIELD,
            )
        )
        if not rows:
            raise ValueError(f"No transactions found with resource ID: {transaction_id}")
        row = rows[0]
        self._immudb.verifiableSQLGet(
            self._TRANSACTIONS_TABLE,
            [PrimaryKeyVarCharValue(value=row["id"])],
        )

        return MoneyFlowMapper.to_domain(row)

    async def create_transaction(self, transaction: MoneyFlowEntity) -> MoneyFlowEntity:
        insert_params: dict = {
            "id": str(transaction.unique_id),
            "user_id": int(transaction.user_id),
            "transaction_id": str(transaction.transaction_id),
            "source_wallet_id": str(transaction.container_id),
            "amount": str(transaction.amount),
            "created_at": transaction.created_at.isoformat(),
        }
        if transaction.cancels_other is not None:
            insert_params["cancels_other"] = str(transaction.cancels_other)
        if transaction.adjusts_other is not None:
            insert_params["adjusts_other"] = str(transaction.adjusts_other)

        sql_columns = ", ".join(insert_params.keys())
        sql_values = ", ".join(f"@{column}" for column in insert_params)
        self._immudb.sqlExec(
            f"INSERT INTO {self._TRANSACTIONS_TABLE} ({sql_columns}) VALUES ({sql_values});",
            insert_params,
        )

        return transaction

    async def get_flows_for_transaction(self, transaction_id: UUID) -> list[MoneyFlowEntity]:
        rows = self._immudb.sqlQuery(
            f"SELECT * FROM {self._TRANSACTIONS_TABLE} WHERE transaction_id = @transaction_id;",
            {"transaction_id": str(transaction_id)},
            COLUMN_NAME_MODE_FIELD,
        )

        return [MoneyFlowMapper.to_domain(row) for row in self._verify(list(rows))]

    async def get_flows_for_transactions(
        self,
        transaction_ids: list[UUID],
    ) -> dict[UUID, list[MoneyFlowEntity]]:
        grouped: dict[UUID, list[MoneyFlowEntity]] = {}
        for transaction_id in transaction_ids:
            grouped[transaction_id] = await self.get_flows_for_transaction(transaction_id)

        return grouped

    async def get_cancelling_flow(
        self,
        transaction_id: UUID,
    ) -> MoneyFlowEntity | None:
        rows = list(
            self._immudb.sqlQuery(
                f"SELECT * FROM {self._TRANSACTIONS_TABLE} WHERE cancels_other = @transaction_id;",
                {"transaction_id": str(transaction_id)},
                COLUMN_NAME_MODE_FIELD,
            )
        )
        if not rows:
            return None

        return MoneyFlowMapper.to_domain(rows[0])

    async def get_adjusting_flow(
        self,
        transaction_id: UUID,
    ) -> MoneyFlowEntity | None:
        rows = list(
            self._immudb.sqlQuery(
                f"SELECT * FROM {self._TRANSACTIONS_TABLE} WHERE adjusts_other = @transaction_id;",
                {"transaction_id": str(transaction_id)},
                COLUMN_NAME_MODE_FIELD,
            )
        )
        if not rows:
            return None

        return MoneyFlowMapper.to_domain(rows[0])

    async def delete_flow_by_id(
        self,
        user_id: int,
        transaction_id: UUID,
    ) -> MoneyFlowEntity:
        existing_cancellation = await self.get_cancelling_flow(transaction_id)
        if existing_cancellation is not None:
            raise ValueError(
                f"Transaction {transaction_id} has already been cancelled "
                f"by {existing_cancellation.unique_id}"
            )

        current_transaction = await self.get_user_flow_by_id(user_id, transaction_id)
        inverse_transaction = current_transaction.create_inverse()
        await self.create_transaction(inverse_transaction)

        return inverse_transaction

    async def get_unsettled_flows(
        self,
        container_id: UUID,
        settled_at: str | None = None,
    ) -> list[MoneyFlowEntity]:
        if settled_at is not None:
            rows = self._immudb.sqlQuery(
                f"SELECT * FROM {self._TRANSACTIONS_TABLE} "
                f"WHERE source_wallet_id = @container_id AND created_at > @settled_at;",
                {"container_id": str(container_id), "settled_at": settled_at},
                COLUMN_NAME_MODE_FIELD,
            )
        else:
            rows = self._immudb.sqlQuery(
                f"SELECT * FROM {self._TRANSACTIONS_TABLE} WHERE source_wallet_id = @container_id;",
                {"container_id": str(container_id)},
                COLUMN_NAME_MODE_FIELD,
            )

        return [MoneyFlowMapper.to_domain(row) for row in self._verify(list(rows))]

    async def get_container_flows_between(
        self,
        container_id: UUID,
        since: datetime | None,
        until: datetime | None,
    ) -> list[MoneyFlowEntity]:
        conditions = ["source_wallet_id = @container_id"]
        parameters: dict = {"container_id": str(container_id)}

        if since is not None:
            conditions.append("created_at >= @since")
            parameters["since"] = since.isoformat()
        if until is not None:
            conditions.append("created_at < @until")
            parameters["until"] = until.isoformat()

        rows = self._immudb.sqlQuery(
            f"SELECT * FROM {self._TRANSACTIONS_TABLE} WHERE {' AND '.join(conditions)};",
            parameters,
            COLUMN_NAME_MODE_FIELD,
        )

        return [MoneyFlowMapper.to_domain(row) for row in self._verify(list(rows))]

    async def get_checkpoint(
        self,
        container_id: UUID,
    ) -> BalanceCheckpointEntity | None:
        checkpoint_rows = list(
            self._immudb.sqlQuery(
                f"SELECT * FROM {self._CHECKPOINTS_TABLE} WHERE wallet_id = @container_id;",
                {"container_id": str(container_id)},
                COLUMN_NAME_MODE_FIELD,
            )
        )

        if not checkpoint_rows:
            return None
        latest_checkpoint = checkpoint_rows[0]

        return BalanceCheckpointEntity(
            id=latest_checkpoint["wallet_id"],
            created_at=datetime.fromisoformat(latest_checkpoint["settled_at"]),
            balance=Decimal(latest_checkpoint["balance"]),
        )

    async def save_checkpoint(self, checkpoint: BalanceCheckpointEntity) -> None:
        self._immudb.sqlExec(
            f"UPSERT INTO {self._CHECKPOINTS_TABLE} "
            f"(wallet_id, balance, settled_at) VALUES (@container_id, @balance, @settled_at);",
            {
                "container_id": str(checkpoint.unique_id),
                "balance": str(checkpoint.balance),
                "settled_at": checkpoint.created_at.isoformat(),
            },
        )
