# Feature Proposals

Implementation proposals for production system concepts. Each folder contains a detailed README covering: motivation, production concepts taught, domain model, implementation notes, and key blockwalls.

## Sprint 1 — Completed

| Feature | Core Concept | Commit |
|---|---|---|
| Health Probes | k8s readiness/liveness — required for deploy | pre-sprint |
| Idempotency Keys | Financial correctness, safe retries | `8b1f18f` |
| Rate Limiting | Redis sliding window throttle | `7c9a63a` |
| Async Migration | ASGI, async views, async ORM, httpx | `9aece66` |
| Ledger-Based Balance (ImmuDB) | Immutable transaction log, derived balance | `a50d5ef` |
| Balance Checkpoint | Celery Beat periodic CQRS read-model | `e245c79` |
| Kubernetes Deployment | Load balancer, PVCs, RBAC, secrets, configmap | `d04dd3f` |

## Remaining Build Order

| Priority | Feature | Core Concept | Done |
|---|---|---|---|
| 1 | [Subscriptions Management](./subscriptions-management/) | State machines, dunning, Celery Beat billing | :x: |
| 2 | [Money Transfers](./money-transfers/) | Distributed atomicity, deadlock prevention | :x: |
| 3 | [OpenTelemetry Tracing](./opentelemetry-tracing/) | Distributed observability for k8s | :x: |
| 4 | [Cursor Pagination](./cursor-pagination/) | Scale-proof pagination, keyset queries | :x: |
| 5 | [Audit Log](./audit-log/) | Immutable ledger, compliance, event history | :x: |
| 6 | [Piggy Bank](./piggy-bank/) | Savings goals, scheduled contributions | :x: |
| 7 | [Split Payments](./split-payments/) | Multi-party billing, debt coordination | :x: |

## System Architecture (after Sprint 1)

```mermaid
graph TB
    subgraph k8s["Kubernetes Cluster"]
        LB[LoadBalancer<br/>django-service :8000]
        subgraph app["Application Pods"]
            Django[Django / ASGI<br/>Uvicorn]
            CeleryWorker[Celery Worker]
            CeleryBeat[Celery Beat]
        end
        subgraph storage["Stateful Services"]
            Postgres[(PostgreSQL<br/>PVC)]
            Redis[(Redis<br/>PVC)]
            RabbitMQ[(RabbitMQ<br/>PVC)]
            ImmuDB[(ImmuDB<br/>PVC)]
        end
    end

    Client --> LB --> Django
    Django --> Postgres
    Django --> Redis
    Django --> ImmuDB
    Django -->|publish event| RabbitMQ
    RabbitMQ --> CeleryWorker
    CeleryWorker --> Postgres
    CeleryWorker --> ImmuDB
    CeleryWorker -->|deliver| Webhook[External Webhook]
    CeleryBeat -->|schedule| CeleryWorker
```

## Ledger + Balance Checkpoint Flow

```mermaid
sequenceDiagram
    participant Client
    participant Django
    participant Postgres
    participant ImmuDB
    participant CeleryBeat as Celery Beat
    participant CeleryWorker as Celery Worker

    Client->>Django: POST /transactions
    Django->>Postgres: persist ORM record
    Django->>ImmuDB: append immutable ledger entry
    Django-->>Client: 201 Created

    Note over CeleryBeat: periodic tick (e.g. every hour)
    CeleryBeat->>CeleryWorker: checkpoint_balance task
    CeleryWorker->>ImmuDB: scan entries since last checkpoint
    CeleryWorker->>ImmuDB: write BalanceCheckpoint record
    Note over ImmuDB: balance = checkpoint + delta
```

## Idempotency Key Flow

```mermaid
sequenceDiagram
    participant Client
    participant Django
    participant Redis
    participant UseCase

    Client->>Django: POST /transactions (Idempotency-Key: abc123)
    Django->>Redis: GET idempotency:abc123
    alt key exists
        Redis-->>Django: cached response
        Django-->>Client: 200 (replay)
    else key absent
        Redis-->>Django: nil
        Django->>UseCase: execute
        UseCase-->>Django: result
        Django->>Redis: SET idempotency:abc123 result (TTL 24h)
        Django-->>Client: 201 Created
    end
```

## Why This Order (Remaining)

Items 1–2 are core financial domain complexity: state machines and distributed atomicity.
Items 3–5 are observability and compliance — production k8s workloads require these.
Items 6–7 are domain feature complexity, lower infrastructure value.
