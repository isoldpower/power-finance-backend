# Subscriptions Management

## Why

Subscriptions introduce recurring state machines, scheduler-driven billing cycles, failure handling for payment retries (dunning), and proration logic. These concepts appear in virtually every SaaS product and map directly to Celery Beat already in the stack.

## Production Concepts Taught

- State machines for lifecycle management
- Scheduler-driven business logic (Celery Beat)
- Dunning — retry logic for failed billing cycles
- Proration on plan changes mid-cycle
- Idempotent billing (pairs with idempotency keys proposal)
- Soft cancellation vs. immediate cancellation
- Event-driven side effects on state transitions

## Domain Model

### Subscription

```
id: UUID
user_id: UUID (FK)
wallet_id: UUID (FK)           — wallet to charge
name: str                       — "Netflix", "Spotify"
amount: Money
billing_cycle: WEEKLY | MONTHLY | YEARLY
status: SubscriptionStatus
next_billing_date: date
trial_ends_at: date | null
cancelled_at: datetime | null
created_at: datetime
updated_at: datetime
```

### SubscriptionStatus (state machine)

```
TRIAL ──────────────► ACTIVE ──────────────► CANCELLED
                         │                       ▲
                         ▼                       │
                     PAST_DUE ──── retry limit ──┘
                         │
                         ▼
                     SUSPENDED
```

| Status | Meaning |
|---|---|
| `TRIAL` | Free trial period, billing not yet started |
| `ACTIVE` | Billing succeeding, subscription current |
| `PAST_DUE` | Last billing attempt failed, retrying |
| `SUSPENDED` | Max retries exhausted, access revoked |
| `CANCELLED` | User cancelled or non-recoverable failure |

### BillingAttempt

```
id: UUID
subscription_id: UUID (FK)
amount: Money
status: PENDING | SUCCESS | FAILED
attempted_at: datetime
transaction_id: UUID | null     — set on success
failure_reason: str | null
retry_count: int
next_retry_at: datetime | null
```

## Celery Beat Tasks

```python
# Every hour — find subscriptions due for billing
@app.task
def process_due_subscriptions():
    subs = Subscription.objects.filter(
        status__in=[ACTIVE, TRIAL],
        next_billing_date__lte=today()
    )
    for sub in subs:
        charge_subscription.delay(sub.id)

# Retry failed billing attempts (dunning)
@app.task
def retry_failed_billing():
    attempts = BillingAttempt.objects.filter(
        status=FAILED,
        next_retry_at__lte=now(),
        retry_count__lt=MAX_RETRIES
    )
    for attempt in attempts:
        retry_billing_attempt.delay(attempt.id)
```

## Dunning Schedule

```
Attempt 1: immediate
Attempt 2: +3 days  → status: PAST_DUE
Attempt 3: +7 days
Attempt 4: +14 days → status: SUSPENDED if still failing
```

## State Transitions

```
trial_ends        → TRIAL     → ACTIVE      (first successful charge)
billing_success   → ACTIVE    → ACTIVE      (next_billing_date advances)
billing_failure   → ACTIVE    → PAST_DUE    (start dunning)
retry_success     → PAST_DUE  → ACTIVE      (dunning resolved)
retry_exhausted   → PAST_DUE  → SUSPENDED
user_cancel       → any       → CANCELLED   (at period end or immediate)
reactivate        → SUSPENDED → ACTIVE      (user updates payment method)
```

## Proration

When user upgrades/downgrades mid-cycle:

```
remaining_days = days_left_in_cycle / cycle_length
credit = old_price * remaining_days
charge = new_price * remaining_days
net_charge = charge - credit
```

Create `ADJUSTMENT` transaction for net difference (maps to existing `TransactionType.ADJUSTMENT`).

## APIs

```
POST   /subscriptions/                  — create
GET    /subscriptions/                  — list
GET    /subscriptions/{id}/             — detail
PUT    /subscriptions/{id}/             — update (amount, name)
POST   /subscriptions/{id}/cancel/      — cancel (immediate or end of period)
POST   /subscriptions/{id}/reactivate/  — reactivate suspended
GET    /subscriptions/{id}/history/     — billing attempt history
```

## Key Blockwalls

- Idempotent billing — Celery task may execute twice; must not double-charge
- Clock issues — what is "today" in a distributed system? Use UTC everywhere
- Race condition — scheduler picks up same subscription twice under load (use DB-level locking or atomic status update)
- Timezone-aware billing dates — user in UTC+9 expects billing on "their" date
- Soft cancellation — access until period end vs. immediate; must track both `cancelled_at` and `access_until`
