# Split Payments for Subscriptions

## Why

Split payments introduce multi-party financial coordination: one subscription, multiple payers, partial settlements, debt tracking, and group lifecycle management. It extends both the subscriptions and money transfers domains while adding genuinely complex business logic around fairness, defaults, and group consensus.

## Production Concepts Taught

- Multi-party transaction coordination
- Debt graph and settlement algorithms
- Group lifecycle management (invitations, acceptance, removal)
- Partial payment collection before charge
- Handling non-paying members (defaults)
- Event choreography across multiple participants
- Composite state derived from participant states

## Domain Model

### SplitGroup

```
id: UUID
subscription_id: UUID (FK)       — the subscription being split
owner_id: UUID (FK User)         — who manages the group
name: str                         — "Netflix Family Plan"
status: SplitGroupStatus
split_type: EQUAL | CUSTOM | PERCENTAGE
created_at: datetime
```

### SplitGroupMember

```
id: UUID
group_id: UUID (FK)
user_id: UUID (FK)
wallet_id: UUID (FK)             — wallet to charge
share_amount: Money | null       — for CUSTOM split
share_percentage: Decimal | null — for PERCENTAGE split
status: MemberStatus
joined_at: datetime | null
invited_at: datetime
```

### SplitGroupStatus

```
FORMING ──► ACTIVE ──► SUSPENDED ──► DISSOLVED
  │           │
  │           └──► MEMBER_DEFAULTED (sub-state, auto-recovers)
  │
  └──► CANCELLED (owner cancels before activation)
```

### MemberStatus

```
INVITED ──► ACCEPTED ──► ACTIVE
    │           │           │
    └──► DECLINED           └──► DEFAULTED ──► REMOVED
                            │
                            └──► LEFT
```

## Split Type Logic

### EQUAL

```python
member_share = subscription.amount / len(active_members)
# Handle remainder: assign to owner or round-robin
```

### PERCENTAGE

```python
member_share = subscription.amount * (member.share_percentage / 100)
# Validate: sum of all percentages == 100
```

### CUSTOM

```python
# Validate: sum of all share_amounts == subscription.total_amount
```

## Billing Cycle Flow

```
1. Billing cycle starts (Celery Beat, same as subscriptions)
2. Create BillingRound for this cycle
3. Collect from each ACTIVE member's wallet:
   - SUCCESS: mark member payment as PAID
   - FAILURE: mark as DEFAULTED, notify owner
4. If all members paid:
   - Total collected == subscription amount → execute full subscription charge
5. If partial collection:
   - Configurable policy: charge anyway (owner covers shortfall) or suspend subscription
```

### BillingRound

```
id: UUID
group_id: UUID (FK)
billing_period_start: date
billing_period_end: date
status: PENDING | COLLECTING | COMPLETE | PARTIAL | FAILED
total_expected: Money
total_collected: Money
created_at: datetime
```

### MemberPayment

```
id: UUID
billing_round_id: UUID (FK)
member_id: UUID (FK)
expected_amount: Money
status: PENDING | PAID | DEFAULTED | WAIVED
transaction_id: UUID | null
attempted_at: datetime | null
```

## Default Handling Policies

When a member defaults on payment, the group must decide:

| Policy | Behavior |
|---|---|
| `OWNER_COVERS` | Owner's share increases to cover defaulted amount |
| `EQUAL_DISTRIBUTION` | Shortfall split equally among paying members |
| `SUSPEND_ON_DEFAULT` | Subscription suspended until default resolved |
| `CHARGE_ANYWAY` | Proceed with partial collection, owner pays remainder |

Policy is set at group creation and can be updated by owner.

## Member Removal

When removing a defaulted member mid-cycle:
1. Calculate their paid portion of current cycle
2. No refund for paid cycles, no charge for future cycles
3. Recalculate shares for remaining members
4. If EQUAL split: all shares increase proportionally
5. Create adjustment transactions if necessary

## APIs

```
POST   /split-groups/                           — create group
GET    /split-groups/                           — list my groups (owner + member)
GET    /split-groups/{id}/                      — detail + member list
PUT    /split-groups/{id}/                      — update (policy, name)
POST   /split-groups/{id}/invite/               — invite user
POST   /split-groups/{id}/members/{id}/remove/  — remove member
POST   /split-groups/{id}/dissolve/             — dissolve group

POST   /split-groups/{id}/invitations/{id}/accept/   — accept invite
POST   /split-groups/{id}/invitations/{id}/decline/  — decline invite

GET    /split-groups/{id}/billing/              — billing round history
GET    /split-groups/{id}/billing/{round_id}/   — round detail + per-member status
```

## Notifications

Use existing notification + webhook infrastructure:
- Member invited
- Member accepted / declined
- Member defaulted
- Billing round completed
- Group status changed
- Share amount changed (recalculation)

## Key Blockwalls

- Fractional amounts — `subscription.amount / 3` leaves remainder; must decide allocation deterministically
- Concurrent billing collection — two Celery workers collecting from two members simultaneously; BillingRound must use DB-level locking
- Member leaves mid-cycle — pro-rate or full cycle charge?
- Currency mismatch — members could have wallets in different currencies; scope to same currency initially
- Group quorum — how many members must accept before group activates? All? Majority?
- Idempotent collection — Celery retry must not double-charge a member who already paid
