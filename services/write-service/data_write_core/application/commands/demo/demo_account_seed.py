from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from decimal import Decimal
from typing import NamedTuple
from uuid import UUID, uuid5

from data_write_core.domain.value_objects import CategoryKind, TransactionType, global_category_id

from ...bootstrap import get_repository_registry
from ...interfaces import DemoSeedRepository
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


DEMO_SEED_ITEM_NAMESPACE = UUID("5d1f0c7e-3a9b-4c62-8e47-b2a6f9d18c35")


def demo_seed_item_id(external_id: str, item_key: str) -> UUID:
    return uuid5(DEMO_SEED_ITEM_NAMESPACE, f"{external_id}:{item_key}")


class DemoSeedItem(NamedTuple):
    item_id: UUID
    create: Callable[[], Awaitable[int]]


class DemoAccountSeeder:
    def __init__(self, seed_repository: DemoSeedRepository | None = None) -> None:
        self._seed_repository = seed_repository or get_repository_registry().demo_seed_repository

    async def seed_if_incomplete(self, user_id: int, external_id: str) -> int | None:
        if await self._seed_repository.is_seed_completed(user_id):
            return None

        seed_items = self._plan(user_id, external_id)
        existing_item_ids = await self._seed_repository.find_existing_seed_items(
            user_id, [seed_item.item_id for seed_item in seed_items]
        )
        write_versions = [
            await self._create_unless_present(user_id, seed_item)
            for seed_item in seed_items
            if seed_item.item_id not in existing_item_ids
        ]
        await self._seed_repository.mark_seed_completed(user_id)

        created_write_versions = [version for version in write_versions if version is not None]
        return max(created_write_versions) if created_write_versions else None

    async def _create_unless_present(self, user_id: int, seed_item: DemoSeedItem) -> int | None:
        try:
            return await seed_item.create()
        except Exception:
            concurrently_created = await self._seed_repository.find_existing_seed_items(
                user_id, [seed_item.item_id]
            )
            if seed_item.item_id in concurrently_created:
                return None
            raise

    @staticmethod
    def _plan(user_id: int, external_id: str) -> list[DemoSeedItem]:
        container_ids = {
            wallet_seed.key: demo_seed_item_id(external_id, f"wallet:{wallet_seed.key}")
            for wallet_seed in DEMO_WALLETS
        }
        container_ids[DEMO_GOAL.key] = demo_seed_item_id(external_id, f"goal:{DEMO_GOAL.key}")

        seed_items = [
            DemoSeedItem(
                item_id=container_ids[wallet_seed.key],
                create=_wallet_creator(
                    user_id, external_id, container_ids[wallet_seed.key], wallet_seed
                ),
            )
            for wallet_seed in DEMO_WALLETS
        ]
        seed_items.append(
            DemoSeedItem(
                item_id=container_ids[DEMO_GOAL.key],
                create=_goal_creator(user_id, external_id, container_ids[DEMO_GOAL.key]),
            )
        )
        for transaction_position, transaction_seed in enumerate(DEMO_TRANSACTIONS):
            transaction_id = demo_seed_item_id(external_id, f"transaction:{transaction_position}")
            seed_items.append(
                DemoSeedItem(
                    item_id=transaction_id,
                    create=_transaction_creator(
                        user_id,
                        external_id,
                        transaction_id,
                        container_ids[transaction_seed.container_key],
                        transaction_seed,
                    ),
                )
            )

        return seed_items


def _wallet_creator(
    user_id: int,
    external_id: str,
    wallet_id: UUID,
    wallet_seed: DemoWalletSeed,
) -> Callable[[], Awaitable[int]]:
    async def create_wallet() -> int:
        _, write_version = await CreateNewWalletCommandHandler().handle(
            CreateNewWalletCommand(
                user_id=user_id,
                user_external_id=external_id,
                name=wallet_seed.name,
                currency=wallet_seed.currency,
                category_id=global_category_id(CategoryKind.WALLET, wallet_seed.category),
                color=wallet_seed.color,
                opening_balance=wallet_seed.opening_balance,
                wallet_id=wallet_id,
            )
        )
        return write_version

    return create_wallet


def _goal_creator(user_id: int, external_id: str, goal_id: UUID) -> Callable[[], Awaitable[int]]:
    async def create_goal() -> int:
        _, write_version = await CreateNewGoalCommandHandler().handle(
            CreateNewGoalCommand(
                user_id=user_id,
                user_external_id=external_id,
                name=DEMO_GOAL.name,
                currency=DEMO_GOAL.currency,
                target=DEMO_GOAL.target,
                finish_at=datetime.now() + timedelta(days=DEMO_GOAL.days_until_finish),
                goal_id=goal_id,
            )
        )
        return write_version

    return create_goal


def _transaction_creator(
    user_id: int,
    external_id: str,
    transaction_id: UUID,
    container_id: UUID,
    transaction_seed: DemoTransactionSeed,
) -> Callable[[], Awaitable[int]]:
    async def create_transaction() -> int:
        _, write_version = await CreateTransactionCommandHandler().handle(
            CreateTransactionCommand(
                user_id=user_id,
                user_external_id=external_id,
                wallet_id=container_id,
                amount=transaction_seed.amount,
                name=transaction_seed.name,
                category_id=global_category_id(CategoryKind.TRANSACTION, transaction_seed.category),
                transaction_type=transaction_seed.transaction_type,
                transaction_id=transaction_id,
            )
        )
        return write_version

    return create_transaction
