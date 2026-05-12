# Piggy Bank (Savings Goals)

## Why

Piggy bank introduces goal-based fund allocation, progress tracking, scheduled contributions, and partial withdrawal logic. It's a good domain complexity exercise with a clear state machine and pairs well with the subscription scheduler already in the stack.

## Production Concepts Taught

- Goal lifecycle state machine
- Scheduled automatic contributions (Celery Beat)
- Fund allocation and reservation (sub-wallet concept)
- Progress calculation and projections
- Partial vs. full withdrawals
- Goal completion and celebration events (webhooks/notifications)

## Domain Model

### SavingsGoal

```
id: UUID
user_id: UUID (FK)
source_wallet_id: UUID (FK)     — wallet to deduct from
name: str                        — "New Laptop", "Vacation Fund"
description: str | null
target_amount: Money
current_amount: Money            — amount saved so far
status: GoalStatus
target_date: date | null         — optional deadline
auto_contribute: bool
contribution_amount: Money | null
contribution_frequency: WEEKLY | MONTHLY | null
next_contribution_date: date | null
created_at: datetime
completed_at: datetime | null
```

### GoalStatus

```
ACTIVE ──────────────► COMPLETED  (current_amount >= target_amount)
  │                        
  ├──────────────────► PAUSED     (user pauses contributions)
  │    ◄────────────── PAUSED     (user resumes)
  │                        
  └──────────────────► CANCELLED  (user cancels, funds returned to wallet)
```

### GoalContribution

```
id: UUID
goal_id: UUID (FK)
amount: Money
contribution_type: MANUAL | AUTOMATIC
transaction_id: UUID (FK)        — linked Transaction record
created_at: datetime
```

## Fund Allocation

Two approaches:

**Virtual allocation (simpler):**
Funds stay in wallet, goal just tracks a `current_amount` counter. No actual fund movement until withdrawal.

```
Wallet balance: 1000
Goal A target: 500, current: 200   (200 "allocated" but still in wallet)
Goal B target: 300, current: 100   (100 "allocated" but still in wallet)
Free balance: 700 (1000 - 200 - 100)
```

**Physical allocation (harder, more realistic):**
Create a dedicated `SAVINGS` wallet per goal. Contributions move money to that wallet. Withdrawal moves it back.

Physical allocation is more interesting — teaches atomic fund movement.

## APIs

```
POST   /savings-goals/                     — create goal
GET    /savings-goals/                     — list goals
GET    /savings-goals/{id}/                — detail + progress
PUT    /savings-goals/{id}/                — update (name, target, date)
POST   /savings-goals/{id}/contribute/     — manual contribution
POST   /savings-goals/{id}/withdraw/       — withdraw funds
POST   /savings-goals/{id}/pause/          — pause auto-contributions
POST   /savings-goals/{id}/resume/         — resume auto-contributions
POST   /savings-goals/{id}/cancel/         — cancel + return funds
GET    /savings-goals/{id}/contributions/  — contribution history
```

## Progress Tracking

```python
@property
def progress_percentage(self) -> Decimal:
    return (self.current_amount.value / self.target_amount.value) * 100

@property
def remaining_amount(self) -> Money:
    return self.target_amount - self.current_amount

@property
def projected_completion_date(self) -> date | None:
    if not self.contribution_amount or not self.contribution_frequency:
        return None
    periods_needed = ceil(self.remaining_amount / self.contribution_amount)
    return calculate_future_date(self.next_contribution_date, self.contribution_frequency, periods_needed)

@property
def is_on_track(self) -> bool:
    if not self.target_date:
        return None
    return self.projected_completion_date <= self.target_date
```

## Celery Beat Task

```python
@app.task
def process_automatic_contributions():
    goals = SavingsGoal.objects.filter(
        status=GoalStatus.ACTIVE,
        auto_contribute=True,
        next_contribution_date__lte=today()
    )
    for goal in goals:
        contribute_to_goal.delay(goal.id, is_automatic=True)
```

## Completion Event

When `current_amount >= target_amount`:
1. Set `status = COMPLETED`, `completed_at = now()`
2. Fire domain event `GoalCompleted`
3. Domain event triggers webhook + notification (existing infrastructure)
4. Optional: auto-transfer to main wallet or keep allocated

## Withdrawal Rules

```
FULL withdrawal:
  - Move all current_amount back to source_wallet
  - Set current_amount = 0
  - Status: CANCELLED (if user decides to abandon) or stays ACTIVE

PARTIAL withdrawal:
  - Move requested amount back to source_wallet
  - Reduce current_amount by withdrawn amount
  - Goal stays ACTIVE (progress reduced)
```

## Key Blockwalls

- Insufficient source wallet balance for auto-contribution — must handle gracefully (skip + notify, not fail silently)
- Goal wallet vs. virtual allocation — physical approach requires atomic fund movement (same pattern as money transfers)
- Multiple goals competing for same wallet balance — must validate against free balance, not total balance
- Withdrawal after goal completed — decide policy: locked for a period, or freely withdrawable
- Contribution partially fills goal — detect overfill, contribute only the remainder
