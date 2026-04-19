from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from immudb.constants import COLUMN_NAME_MODE_FIELD

from finances.application.interfaces import TransactionSelectorsCollection
from finances.application.bootstrap.state import ImmudbConnection


class ImmudbTransactionSelectorsCollection(TransactionSelectorsCollection):
    def __init__(self, immudb_client: ImmudbConnection):
        self._immudb = immudb_client.client
        self._table = 'transactions'

    async def get_expenses_by_category(self, user_id: int) -> list[dict[str, str]]:
        return []

    async def get_monthly_expenditure_and_income(self, user_id: int) -> list[dict[str, str]]:
        rows = self._immudb.sqlQuery(
            f'SELECT amount, created_at FROM {self._table} WHERE user_id = @user_id;',
            {'user_id': user_id},
            COLUMN_NAME_MODE_FIELD,
        )

        monthly: dict[str, dict] = defaultdict(lambda: {
            'income': Decimal(0), 'expenses': Decimal(0), '_dt': None,
        })
        for row in rows:
            amount = Decimal(str(row['amount']))
            dt = datetime.fromisoformat(row['created_at'])
            key = dt.strftime('%Y-%m')
            monthly[key]['_dt'] = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if amount > 0:
                monthly[key]['income'] += amount
            else:
                monthly[key]['expenses'] += abs(amount)

        return [
            {'month': data['_dt'], 'income': data['income'], 'expenses': data['expenses']}
            for _, data in sorted(monthly.items())
            if data['_dt'] is not None
        ]

    async def get_user_transfers_grouped(self, user_id: int) -> list[dict[str, str]]:
        return []

    async def get_daily_spending(self, user_id: int) -> list[dict[str, any]]:
        rows = self._immudb.sqlQuery(
            f'SELECT amount, created_at FROM {self._table} WHERE user_id = @user_id;',
            {'user_id': user_id},
            COLUMN_NAME_MODE_FIELD,
        )

        daily: dict = defaultdict(Decimal)
        for row in rows:
            amount = Decimal(str(row['amount']))
            if amount < 0:
                day = datetime.fromisoformat(row['created_at']).date()
                daily[day] += abs(amount)

        return [{'day': day, 'total': total} for day, total in sorted(daily.items())]

    async def get_wallet_transactions(self, wallet_id: UUID) -> list[dict[str, any]]:
        rows = self._immudb.sqlQuery(
            f'SELECT source_wallet_id, amount, created_at FROM {self._table} WHERE source_wallet_id = @wallet_id;',
            {'wallet_id': str(wallet_id)},
            COLUMN_NAME_MODE_FIELD,
        )

        result = []
        for row in rows:
            amount = Decimal(str(row['amount']))
            created_at = datetime.fromisoformat(row['created_at'])
            if amount >= 0:
                result.append({
                    'send_wallet_id': None,
                    'receive_wallet_id': wallet_id,
                    'send_amount': None,
                    'receive_amount': amount,
                    'created_at': created_at,
                })
            else:
                result.append({
                    'send_wallet_id': wallet_id,
                    'receive_wallet_id': None,
                    'send_amount': abs(amount),
                    'receive_amount': None,
                    'created_at': created_at,
                })

        return sorted(result, key=lambda r: r['created_at'])
