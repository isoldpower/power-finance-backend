# immudb as Transaction Source of Truth

## Why

Financial transactions must be tamper-proof by design, not just by policy. Storing transactions in PostgreSQL allows any operator with DB access to mutate or erase records. Moving transactions to immudb provides cryptographic proof of immutability — each record is chained and verifiable via `verifiedGet`. Cancellations are expressed as new ADJUSTMENT transactions, preserving the full audit trail.

## Production Concepts Taught

- Append-only ledger design (no UPDATE, no DELETE)
- Adjustment/reversal transactions instead of logical deletes
- Dual-store architecture: immudb (source of truth) + PostgreSQL (wallets, users)
- Wrapping sync SDKs for async Django via `sync_to_async`
- Balance checkpoints as settled snapshots (reduce replay cost)
- immudb SQL — schema creation, indexed queries, parameterized statements

## Core Concept

```
PostgreSQL model:  DELETE FROM transactions WHERE id = 'x'
                   → record gone, balance rollback hidden

immudb model:      INSERT INTO transactions (id, type, cancels_id, ...)
                   VALUES (new_uuid, 'adjustment', 'x', ...)
                   → original preserved, cancellation visible, both provable
```

## Target Architecture

```
Create TX  → write immudb transactions table
             → update wallet balance in PostgreSQL

Cancel TX  → create ADJUSTMENT tx in immudb (mirrors original, flipped sign)
             → update wallet balance in PostgreSQL

Every 12h  → Celery task reads all wallets
             → writes balance_checkpoints to immudb
             → checkpoint = settled, auditable, no further replay needed
```

## Migration Steps

### Step 1 — immudb Schema Init (`bootstrap/immudb.py`)

After `client.useDatabase(...)`, run `sqlexec` to create tables:

```sql
CREATE TABLE IF NOT EXISTS transactions (
    id            VARCHAR[36]  NOT NULL,
    user_id       INTEGER      NOT NULL,
    send_wallet   VARCHAR[36],
    send_amount   VARCHAR[32],
    send_currency VARCHAR[8],
    recv_wallet   VARCHAR[36],
    recv_amount   VARCHAR[32],
    recv_currency VARCHAR[8],
    description   VARCHAR[512],
    type          VARCHAR[32]  NOT NULL,
    category      VARCHAR[32]  NOT NULL,
    created_at    VARCHAR[32]  NOT NULL,
    cancels_id    VARCHAR[36],
    PRIMARY KEY   id
);

CREATE INDEX IF NOT EXISTS ON transactions(user_id);
CREATE INDEX IF NOT EXISTS ON transactions(send_wallet);
CREATE INDEX IF NOT EXISTS ON transactions(recv_wallet);

CREATE TABLE IF NOT EXISTS balance_checkpoints (
    wallet_id     VARCHAR[36]  NOT NULL,
    balance       VARCHAR[32]  NOT NULL,
    currency      VARCHAR[8]   NOT NULL,
    settled_at    VARCHAR[32]  NOT NULL,
    last_tx_id    VARCHAR[36],
    PRIMARY KEY   wallet_id
);
```

Amounts stored as `VARCHAR` (decimal string) — immudb has no DECIMAL type.

### Step 2 — `Transaction` Domain Entity

File: `finances/domain/entities/transaction.py`

- Add field: `cancels_id: UUID | None = None`
- Add classmethod `Transaction.create_adjustment(original: Transaction) → Transaction`:
  - Flips sender/receiver
  - Sets `type = TransactionType.ADJUSTMENT`
  - Sets `cancels_id = original.id`
  - Emits `TransactionCreatedEvent` (adjustment is a real transaction)
- Remove `update_fields()` — transactions are immutable after creation
- Remove `confirm_delete()` — deletions no longer exist

Remove from `finances/domain/events/`:
- `TransactionUpdatedEvent`
- `TransactionDeletedEvent`

### Step 3 — `TransactionRepository` Interface

File: `finances/application/interfaces/repository/transaction_repository.py`

Remove:
- `save_transaction`
- `delete_transaction_by_id`

Final interface:
```python
async def create_transaction(self, transaction: Transaction) -> Transaction
async def get_user_transaction_by_id(self, user_id: int, transaction_id: UUID) -> Transaction
async def get_user_transactions(self, user_id: int) -> list[Transaction]
async def list_transactions_with_filters(self, tree: ResolvedFilterTree, user_id: int) -> list[Transaction]
```

### Step 4 — `ImmudbTransactionRepository`

New file: `finances/infrastructure/repositories/immudb_transaction_repository.py`

All methods bridge sync immudb SDK via `sync_to_async`:

```python
from asgiref.sync import sync_to_async
from immudb.client import ImmudbClient

class ImmudbTransactionRepository(TransactionRepository):
    def __init__(self, client: ImmudbClient):
        self._client = client

    async def create_transaction(self, transaction: Transaction) -> Transaction:
        await sync_to_async(self._client.sqlexec)(
            "INSERT INTO transactions (...) VALUES (@id, @user_id, ...);",
            {"id": str(transaction.id), ...}
        )
        return transaction

    async def get_user_transaction_by_id(self, user_id: int, transaction_id: UUID) -> Transaction:
        rows = await sync_to_async(self._client.sqlquery)(
            "SELECT * FROM transactions WHERE id = @id AND user_id = @user_id;",
            {"id": str(transaction_id), "user_id": user_id}
        )
        if not rows:
            raise ObjectDoesNotExist(...)
        return _row_to_transaction(rows[0])

    async def get_user_transactions(self, user_id: int) -> list[Transaction]:
        rows = await sync_to_async(self._client.sqlquery)(
            "SELECT * FROM transactions WHERE user_id = @user_id ORDER BY created_at;",
            {"user_id": user_id}
        )
        return [_row_to_transaction(r) for r in rows]

    async def list_transactions_with_filters(self, tree: ResolvedFilterTree, user_id: int) -> list[Transaction]:
        sql, params = tree.to_immudb_sql()
        rows = await sync_to_async(self._client.sqlquery)(
            f"SELECT * FROM transactions WHERE user_id = @user_id AND ({sql});",
            {"user_id": user_id, **params}
        )
        return [_row_to_transaction(r) for r in rows]
```

### Step 5 — Filter Tree: Add immudb SQL Emitter

`ResolvedFilterTree.to_immudb_sql()` is needed for `list_transactions_with_filters`.

Each leaf node and group node needs a second method alongside `django_q()`:

```python
# leaf node example
class EqualLeaf(FilterLeaf):
    def django_q(self) -> Q:
        return Q(**{f"{self.field}__exact": self.value})

    def to_immudb_sql(self) -> tuple[str, dict]:
        key = f"p_{self.field}"
        return f"{self.field} = @{key}", {key: self.value}

# AND group
class AndGroup(FilterGroup):
    def to_immudb_sql(self) -> tuple[str, dict]:
        parts, params = [], {}
        for node in self.nodes:
            sql, p = node.to_immudb_sql()
            parts.append(sql)
            params.update(p)
        return " AND ".join(parts), params
```

Leaf nodes to update (all under `domain/services/filter_parser/leaf_nodes/`):
`equal`, `not_equal`, `greater`, `greater_equal`, `less`, `less_equal`, `contains`, `i_contains`, `in`

Group nodes to update (`group_nodes/`):
`and_group`, `or_group`

### Step 6 — Repurpose `DeleteTransactionCommandHandler`

File: `finances/application/use_cases/commands/delete_transaction.py`

Replace delete logic with adjustment creation:

```python
@atomic_evently_command()
async def handle(self, command: DeleteTransactionCommand) -> TransactionDTO:
    original = await self.transaction_repository.get_user_transaction_by_id(
        user_id=command.user_id,
        transaction_id=UUID(command.transaction_id),
    )
    adjustment = Transaction.create_adjustment(original)
    adjustment.migrate_event_collector(self.event_collector)

    sender_wallet, receiver_wallet = await self._load_affected_wallets(adjustment, command.user_id)
    apply_transaction_to_wallet_balance(adjustment, sender_wallet, receiver_wallet)

    created = await self.transaction_repository.create_transaction(adjustment)
    await self._persist_wallets(sender_wallet, receiver_wallet)

    return transaction_to_dto(created, sender_wallet, receiver_wallet)
```

### Step 7 — Delete `UpdateTransactionCommandHandler`

- Delete `finances/application/use_cases/commands/update_transaction.py`
- Remove from `use_cases/commands/__init__.py`
- Remove HTTP endpoint + serializer + URL for `PATCH /transactions/{id}/`

### Step 8 — Remove `TransactionModel` from Django

- Delete `finances/infrastructure/orm/transaction.py`
- Create new Django migration: `migrations.DeleteModel(name='TransactionModel')`
- Delete `finances/infrastructure/repositories/django_transaction_repository.py`
- Update `finances/infrastructure/repositories/__init__.py`

### Step 9 — Wire `ImmudbTransactionRepository` in Bootstrap

File: `finances/application/bootstrap/__init__.py` (or wherever `RepositoryRegistry` is built)

Replace:
```python
transaction_repository=DjangoTransactionRepository()
```
With:
```python
transaction_repository=ImmudbTransactionRepository(client=app_state.immudb.client)
```

### Step 10 — `settle_balance_checkpoints` Celery Task

New file: `finances/infrastructure/celery/tasks/checkpoint_tasks.py`

```python
from asgiref.sync import async_to_sync
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(name="finances.settle_balance_checkpoints")
def settle_balance_checkpoints() -> None:
    async_to_sync(_settle_balance_checkpoints)()


async def _settle_balance_checkpoints() -> None:
    logger.info("Task [finances.settle_balance_checkpoints]: Starting checkpoint settlement")
    from finances.application.bootstrap import get_repository_registry, get_application_state

    try:
        registry = get_repository_registry()
        state = get_application_state()
        wallets = await registry.wallet_repository.get_all_wallets()

        for wallet in wallets:
            transactions = await registry.transaction_repository.get_user_transactions(wallet.user_id)
            wallet_txs = [
                tx for tx in transactions
                if (tx.sender and tx.sender.wallet_id == wallet.id)
                or (tx.receiver and tx.receiver.wallet_id == wallet.id)
            ]
            last_tx_id = wallet_txs[-1].id if wallet_txs else None

            await sync_to_async(state.immudb.client.sqlexec)(
                """
                UPSERT INTO balance_checkpoints (wallet_id, balance, currency, settled_at, last_tx_id)
                VALUES (@wallet_id, @balance, @currency, @settled_at, @last_tx_id);
                """,
                {
                    "wallet_id": str(wallet.id),
                    "balance": str(wallet.balance.amount),
                    "currency": wallet.balance.currency_code,
                    "settled_at": timezone.now().isoformat(),
                    "last_tx_id": str(last_tx_id) if last_tx_id else "",
                }
            )

        logger.info("Task [finances.settle_balance_checkpoints]: Settled %d wallets", len(wallets))
    except Exception as exc:
        logger.error("Task [finances.settle_balance_checkpoints]: Failed - %s", str(exc))
```

Add to beat schedule in `finances/infrastructure/celery/client.py`:

```python
"settle-balance-checkpoints-every-12-hours": {
    "task": "finances.settle_balance_checkpoints",
    "schedule": 43200.0,  # 12 hours
},
```

## Key Decisions

| Decision | Choice | Reason |
|---|---|---|
| Cancel mechanism | ADJUSTMENT transaction | Preserves full history, immudb stays append-only |
| Amount storage | VARCHAR decimal string | immudb has no DECIMAL type |
| Filter queries | SQL emitter per leaf/group node | Keeps filter tree architecture consistent |
| Sync SDK bridging | `sync_to_async` | Already used project-wide for immudb |
| Checkpoint strategy | UPSERT per wallet (latest only) | Checkpoints are settlement snapshots, not history |
| immudb write failure | Log + raise | Transaction must not silently succeed without ledger entry |

## Key Blockwalls

- **immudb SQL limitations** — no complex JOINs, no DECIMAL, VARCHAR length must be declared. Test queries against real immudb instance early.
- **Filter tree SQL params collision** — if two leaf nodes filter the same field, param key names collide. Add a counter/unique suffix to param keys.
- **`get_all_wallets`** — `WalletRepository` has no `get_all_wallets` method today. Must add interface + impl before Step 10.
- **`user_id` on transactions** — immudb has no FK constraints. `user_id` must be denormalized onto every transaction row for ownership queries.
- **UPSERT in immudb SQL** — verify immudb 1.10 supports `UPSERT INTO`. If not, use SELECT + conditional INSERT/UPDATE via two `sqlexec` calls.
