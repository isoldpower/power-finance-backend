# Audit Log / Immutable Event Ledger

## Why

Financial systems must be able to answer: "What was the balance on Jan 1? Who changed this transaction and when? What exactly happened?" Mutable records can't answer these questions. An append-only audit log provides an immutable history of every state change — required for compliance, debugging, and dispute resolution.

## Production Concepts Taught

- Append-only (immutable) table design
- Event sourcing lite — derive current state from event history
- Actor tracking (who did what)
- Before/after state capture
- Preventing audit log tampering
- Database-level immutability enforcement
- Compliance requirements shaping architecture

## Core Concept

```
Normal DB:  UPDATE wallet SET balance = 500 WHERE id = 1
            → previous balance gone forever

Audit log:  INSERT INTO audit_log (entity, action, before, after, actor, timestamp)
            VALUES ('wallet:1', 'balance_changed', 900, 500, 'user:abc', now())
            → full history preserved
```

## AuditLog Model

```
id: UUID (PK)
entity_type: str             — 'wallet', 'transaction', 'subscription'
entity_id: UUID
action: AuditAction          — see below
actor_id: UUID | null        — user who triggered, null for system
actor_type: HUMAN | SYSTEM | API_KEY
before_state: jsonb | null   — snapshot before change
after_state: jsonb | null    — snapshot after change
ip_address: str | null
user_agent: str | null
request_id: str | null       — correlate with logs/traces
metadata: jsonb              — action-specific extra data
created_at: timestamp        — indexed, never updated

CONSTRAINT: no UPDATE, no DELETE on this table
```

## AuditAction Enum

```python
class AuditAction(str, Enum):
    # Wallet
    WALLET_CREATED = "wallet.created"
    WALLET_UPDATED = "wallet.updated"
    WALLET_DELETED = "wallet.deleted"
    WALLET_BALANCE_CHANGED = "wallet.balance_changed"

    # Transaction
    TRANSACTION_CREATED = "transaction.created"
    TRANSACTION_UPDATED = "transaction.updated"
    TRANSACTION_DELETED = "transaction.deleted"

    # Transfer
    TRANSFER_INITIATED = "transfer.initiated"
    TRANSFER_COMPLETED = "transfer.completed"
    TRANSFER_REVERSED = "transfer.reversed"
    TRANSFER_FAILED = "transfer.failed"

    # Auth
    USER_LOGIN = "auth.login"
    USER_LOGOUT = "auth.logout"

    # Subscription
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_STATUS_CHANGED = "subscription.status_changed"
    BILLING_ATTEMPT = "billing.attempt"
```

## Immutability Enforcement

### PostgreSQL Rule (database-level)

```sql
CREATE RULE audit_log_no_update AS
    ON UPDATE TO audit_log DO INSTEAD NOTHING;

CREATE RULE audit_log_no_delete AS
    ON DELETE TO audit_log DO INSTEAD NOTHING;
```

Even if application code has a bug and tries to `UPDATE`/`DELETE`, the DB silently ignores it.

### Django Model Override

```python
class AuditLog(models.Model):
    # ... fields

    def save(self, *args, **kwargs):
        if self.pk:
            raise PermissionError("AuditLog records are immutable")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("AuditLog records cannot be deleted")

    class Meta:
        managed = True
        # Never bulk_update this model
```

## Integration Points

### Django Signal Approach

```python
@receiver(post_save, sender=Transaction)
def log_transaction_change(sender, instance, created, **kwargs):
    AuditLog.objects.create(
        entity_type='transaction',
        entity_id=instance.id,
        action=AuditAction.TRANSACTION_CREATED if created else AuditAction.TRANSACTION_UPDATED,
        after_state=TransactionSerializer(instance).data,
        actor_id=get_current_user(),   # thread-local or context var
    )
```

### Use Case Layer Approach (cleaner, matches existing architecture)

```python
class CreateTransactionUseCase:
    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service

    def execute(self, command):
        transaction = self.repo.create(...)
        self.audit_service.log(
            entity=transaction,
            action=AuditAction.TRANSACTION_CREATED,
            actor=command.actor,
            after_state=transaction.to_dict(),
        )
```

Use case layer approach preferred — matches existing clean architecture pattern.

## APIs

```
GET /audit-log/                            — list (admin only)
GET /audit-log/?entity_type=wallet&entity_id={id}  — entity history
GET /audit-log/?actor_id={user_id}         — user activity
GET /audit-log/?action=transfer.completed  — filter by action
GET /audit-log/{id}/                       — single entry
```

## Balance History Reconstruction

With audit log, you can reconstruct balance at any point in time:

```python
def get_balance_at(wallet_id: UUID, at: datetime) -> Money:
    entries = AuditLog.objects.filter(
        entity_type='wallet',
        entity_id=wallet_id,
        action='wallet.balance_changed',
        created_at__lte=at
    ).order_by('-created_at').first()

    if entries:
        return Money.from_dict(entries.after_state['balance'])
    return Money.zero()
```

## Storage Considerations

Audit log grows forever. Plan for it:

- Separate DB table, potentially separate schema or DB
- Partition by month (`created_at`) for query performance
- Cold storage archival after 2 years (S3 + Glacier)
- Never put audit log in same transaction as the operation it records — audit log write failure must not roll back the business operation

## Key Blockwalls

- Actor context — how does the audit log know *who* is performing an action deep in a use case? Options: thread-local, request context var, explicit actor parameter in every command
- Async operations — Celery tasks have no HTTP request context; must pass actor explicitly in task payload
- Before-state capture — must snapshot state *before* the change, not after; order matters
- Separate transaction — audit log INSERT in its own transaction means it can fail independently; decide whether to accept that or use outbox pattern
