# Feature Proposals

Implementation proposals for production system concepts. Each folder contains a detailed README covering: motivation, production concepts taught, domain model, implementation notes, and key blockwalls.

## Recommended Build Order

| Priority | Feature                                                 | Core Concept                                 |
|----------|---------------------------------------------------------|----------------------------------------------|
| 1        | [Health Probes](./health-probes/)                       | k8s readiness/liveness — required for deploy |
| 2        | [Idempotency Keys](./idempotency-keys/)                 | Financial correctness, safe retries          |
| 3        | [Rate Limiting](./rate-limiting/)                       | API protection, sliding window, Redis        |
| 4        | [Subscriptions Management](./subscriptions-management/) | State machines, dunning, Celery Beat billing |
| 5        | [Money Transfers](./money-transfers/)                   | Distributed atomicity, deadlock prevention   |
| 6        | [OpenTelemetry Tracing](./opentelemetry-tracing/)       | Distributed observability for k8s            |
| 7        | [Cursor Pagination](./cursor-pagination/)               | Scale-proof pagination, keyset queries       |
| 8        | [Audit Log](./audit-log/)                               | Immutable ledger, compliance, event history  |
| 9        | [Ledger-Based Balance + CQRS](./ledger-cqrs/)           | Event sourcing, derived state, checkpointing |
| 10       | [Piggy Bank](./piggy-bank/)                             | Savings goals, scheduled contributions       |
| 11       | [Split Payments](./split-payments/)                     | Multi-party billing, debt coordination       |

## Why This Order

Items 1–3 are infrastructure foundations — small to implement, high leverage, unblock everything else.
Items 4–5 are the core financial domain complexity: state machines and atomicity.
Items 6–8 are observability and compliance — production systems require these.
Item 9 (ledger CQRS) is high architectural value — teaches event sourcing and fundamentally changes how balance is modeled.
Items 10–11 are domain feature complexity — fun but lower infrastructure value.
