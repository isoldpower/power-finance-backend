# Money Transfers Between Users

## Why

Transferring money between users in the same system is deceptively hard. It introduces distributed atomicity: debit one wallet, credit another — both must succeed or neither must. This is the core challenge of financial systems and teaches you why databases, transactions, and idempotency exist.

## Production Concepts Taught

- Atomic multi-wallet operations (database transactions)
- Deadlock prevention via consistent lock ordering
- Idempotency for financial mutations
- Optimistic vs. pessimistic locking
- Transfer request lifecycle (PENDING → COMPLETED / FAILED / REVERSED)
- User-to-user authorization and acceptance flows
- Insufficient funds handling

## Domain Model

### TransferRequest

```
id: UUID
idempotency_key: str (unique)   — prevent duplicate transfers
sender_id: UUID (FK User)
receiver_id: UUID (FK User)
sender_wallet_id: UUID (FK Wallet)
receiver_wallet_id: UUID (FK Wallet)
amount: Money
status: TransferStatus
note: str | null
expires_at: datetime | null     — for request-based flows
created_at: datetime
completed_at: datetime | null
failed_reason: str | null
```

### TransferStatus

```
PENDING ──────────────► COMPLETED
    │                       
    ├──────────────────► FAILED
    │                       
    └──────────────────► REVERSED
         ▲
         │
     REVERSING
```

| Status | Meaning |
|---|---|
| `PENDING` | Validated, awaiting execution |
| `COMPLETED` | Both legs executed successfully |
| `FAILED` | Execution failed (insufficient funds, etc.) |
| `REVERSING` | Reversal in progress |
| `REVERSED` | Both legs reversed |

## The Atomicity Problem

Naive implementation:

```python
# WRONG — not atomic
sender_wallet.balance -= amount    # succeeds
receiver_wallet.balance += amount  # fails → sender lost money
```

Correct implementation using database transaction + row-level locking:

```python
with transaction.atomic():
    # Lock both wallets in CONSISTENT ORDER to prevent deadlock
    # Always lock lower UUID first
    wallet_ids = sorted([sender_wallet_id, receiver_wallet_id])
    wallets = Wallet.objects.select_for_update().filter(
        id__in=wallet_ids
    ).order_by('id')

    sender = next(w for w in wallets if w.id == sender_wallet_id)
    receiver = next(w for w in wallets if w.id == receiver_wallet_id)

    if sender.balance < amount:
        raise InsufficientFundsError()

    sender.balance -= amount
    receiver.balance += amount

    sender.save(update_fields=['balance'])
    receiver.save(update_fields=['balance'])

    # Create Transaction records for both legs
    create_transfer_transactions(sender, receiver, amount, transfer_id)
```

## Deadlock Prevention

If two simultaneous transfers cross the same wallets in opposite directions:

```
Transfer A: wallet_1 → wallet_2   (locks wallet_1, then wallet_2)
Transfer B: wallet_2 → wallet_1   (locks wallet_2, then wallet_1)
```

This deadlocks. Fix: always acquire locks in the same global order (sort by UUID). Both transfers lock `wallet_1` first — one waits while the other completes.

## Transaction Records Created

Each completed transfer creates two `Transaction` records:

```
TRANSFER_DEBIT:
  type: TRANSFER
  wallet: sender_wallet
  amount: -amount
  transfer_id: UUID

TRANSFER_CREDIT:
  type: TRANSFER
  wallet: receiver_wallet
  amount: +amount
  transfer_id: UUID
```

Both share a `transfer_id` for traceability. Maps to existing `TransactionType.TRANSFER`.

## APIs

```
POST /transfers/                        — initiate transfer (idempotency key required)
GET  /transfers/                        — list (sent + received)
GET  /transfers/{id}/                   — detail
POST /transfers/{id}/reverse/           — reverse completed transfer
```

## Reversal Flow

Reversal re-runs the same atomic logic in reverse. Must check:
1. Transfer is in `COMPLETED` state
2. Receiver has sufficient balance to reverse
3. Create reversal `Transaction` records with reference to original

## Validation

```
sender != receiver           — no self-transfers
same currency                — no cross-currency (for now)
sender_wallet.user == sender — user owns source wallet
balance >= amount            — sufficient funds check
amount > 0                   — positive amount
```

## Key Blockwalls

- Deadlock from inconsistent lock ordering — solve with sorted UUID locking
- Idempotency — Celery retry or network retry must not double-execute; check idempotency key before acquiring locks
- Cross-currency transfers — requires exchange rate snapshot at time of transfer
- Reversal after receiver spent the money — must decide: block reversal or allow overdraft
- Concurrent balance reads — `SELECT FOR UPDATE` required, not `SELECT`
