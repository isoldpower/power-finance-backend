from datetime import datetime, timedelta
from decimal import Decimal
from typing import NamedTuple
from uuid import UUID

from data_write_core.domain.value_objects import TransactionType

from ..goals.create_new_goal import CreateNewGoalCommand, CreateNewGoalCommandHandler
from ..transactions.create_transaction import (
    CreateTransactionCommand,
    CreateTransactionCommandHandler,
)
from ..wallets.create_new_wallet import CreateNewWalletCommand, CreateNewWalletCommandHandler


class DemoWalletSeed(NamedTuple):
    key: str
    name: str
    currency: str
    category: str
    color: str
    opening_balance: Decimal


class DemoGoalSeed(NamedTuple):
    key: str
    name: str
    currency: str
    target: Decimal
    days_until_finish: int


class DemoTransactionSeed(NamedTuple):
    container_key: str
    name: str
    category: str
    amount: Decimal
    transaction_type: TransactionType


DEMO_WALLETS: tuple[DemoWalletSeed, ...] = (
    DemoWalletSeed("everyday", "Everyday account", "USD", "Banking", "#4F46E5", Decimal("2450.00")),
    DemoWalletSeed("savings", "Savings", "USD", "Savings", "#059669", Decimal("8200.00")),
    DemoWalletSeed("travel", "Travel card", "EUR", "Travel", "#D97706", Decimal("640.00")),
)

DEMO_GOAL = DemoGoalSeed("trip", "Summer trip", "USD", Decimal("3000.00"), 120)

DEMO_TRANSACTIONS: tuple[DemoTransactionSeed, ...] = (
    DemoTransactionSeed("everyday", "Salary", "Income", Decimal("3850.00"), TransactionType.INCOME),
    DemoTransactionSeed("everyday", "Rent", "Housing", Decimal("1450.00"), TransactionType.EXPENSE),
    DemoTransactionSeed("everyday", "Groceries", "Food", Decimal("86.40"), TransactionType.EXPENSE),
    DemoTransactionSeed(
        "everyday", "Coffee shop", "Food", Decimal("6.75"), TransactionType.EXPENSE
    ),
    DemoTransactionSeed(
        "everyday", "Electricity bill", "Utilities", Decimal("72.18"), TransactionType.EXPENSE
    ),
    DemoTransactionSeed(
        "everyday",
        "Streaming subscription",
        "Entertainment",
        Decimal("15.99"),
        TransactionType.EXPENSE,
    ),
    DemoTransactionSeed(
        "everyday", "Gym membership", "Health", Decimal("39.00"), TransactionType.EXPENSE
    ),
    DemoTransactionSeed(
        "everyday", "Restaurant dinner", "Food", Decimal("64.20"), TransactionType.EXPENSE
    ),
    DemoTransactionSeed(
        "savings", "Monthly savings transfer", "Savings", Decimal("500.00"), TransactionType.INCOME
    ),
    DemoTransactionSeed("savings", "Interest", "Income", Decimal("21.37"), TransactionType.INCOME),
    DemoTransactionSeed(
        "travel", "Train tickets", "Travel", Decimal("48.90"), TransactionType.EXPENSE
    ),
    DemoTransactionSeed(
        "travel", "Museum entry", "Leisure", Decimal("18.00"), TransactionType.EXPENSE
    ),
    DemoTransactionSeed(
        "trip", "Trip fund deposit", "Savings", Decimal("750.00"), TransactionType.INCOME
    ),
)


class DemoAccountSeeder:
    async def seed(self, user_id: int, external_id: str) -> None:
        container_ids = await self._create_wallets(user_id, external_id)
        container_ids[DEMO_GOAL.key] = await self._create_goal(user_id, external_id)
        await self._create_transactions(user_id, external_id, container_ids)

    @staticmethod
    async def _create_wallets(user_id: int, external_id: str) -> dict[str, UUID]:
        container_ids: dict[str, UUID] = {}
        for wallet_seed in DEMO_WALLETS:
            created_wallet, _ = await CreateNewWalletCommandHandler().handle(
                CreateNewWalletCommand(
                    user_id=user_id,
                    user_external_id=external_id,
                    name=wallet_seed.name,
                    currency=wallet_seed.currency,
                    category=wallet_seed.category,
                    color=wallet_seed.color,
                    opening_balance=wallet_seed.opening_balance,
                )
            )
            container_ids[wallet_seed.key] = created_wallet.id

        return container_ids

    @staticmethod
    async def _create_goal(user_id: int, external_id: str) -> UUID:
        created_goal, _ = await CreateNewGoalCommandHandler().handle(
            CreateNewGoalCommand(
                user_id=user_id,
                user_external_id=external_id,
                name=DEMO_GOAL.name,
                currency=DEMO_GOAL.currency,
                target=DEMO_GOAL.target,
                finish_at=datetime.now() + timedelta(days=DEMO_GOAL.days_until_finish),
            )
        )
        return created_goal.id

    @staticmethod
    async def _create_transactions(
        user_id: int,
        external_id: str,
        container_ids: dict[str, UUID],
    ) -> None:
        for transaction_seed in DEMO_TRANSACTIONS:
            await CreateTransactionCommandHandler().handle(
                CreateTransactionCommand(
                    user_id=user_id,
                    user_external_id=external_id,
                    wallet_id=container_ids[transaction_seed.container_key],
                    amount=transaction_seed.amount,
                    name=transaction_seed.name,
                    category=transaction_seed.category,
                    transaction_type=transaction_seed.transaction_type,
                )
            )
