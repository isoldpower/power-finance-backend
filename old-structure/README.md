# Power Finance Backend

A robust financial management backend built with Django, utilizing Domain-Driven Design (DDD) principles and Clean Architecture.

## Features

*   **Wallet Management**: Track multiple wallets; balances are derived from an immutable transaction ledger (ImmuDB).
*   **Transaction Tracking**: Double-entry ledger with tamper-evident storage in ImmuDB; periodic balance checkpoints via Celery Beat.
*   **Advanced Analytics**: Spending heatmaps, category breakdowns, and money flow analysis.
*   **Webhooks Service**: Resilient event subscription system with token rotation and automated async delivery retries.
*   **Real-time Notifications**: REST acknowledgment and Server-Sent Events (SSE) streaming.
*   **Advanced Search**: High-performance filtering with a composable filter-tree DSL for all financial records.
*   **Idempotency Keys**: Redis-backed idempotency on all mutating endpoints — safe for client retries.
*   **Rate Limiting**: Redis sliding-window throttle applied per-user across all endpoints.
*   **Async Runtime**: Fully async Django/ASGI stack (Uvicorn + async ORM + httpx).
*   **Secure Authentication**: Clerk JWT with local user-profile sync.
*   **Kubernetes-Ready**: Full k8s manifests — Deployments, PVCs, Services, RBAC, ConfigMap, Secrets, NetworkPolicies.
*   **Layered Architecture**: Domain → Application → Infrastructure → Presentation (DDD/Clean Architecture).

---

## Getting Started

### Prerequisites

*   **Python 3.12+**
*   **Docker & Docker Compose** (local dev) or **Kubernetes** (production)
*   **PostgreSQL**, **Redis**, **RabbitMQ**, **ImmuDB** — all managed via Docker Compose or k8s manifests

### Setup Instructions

1.  **Clone the Repository**:
    ```bash
    git clone [repository-url]
    cd power-finance-backend
    ```

2.  **Environment Configuration**:
    Copy `.env.sample` to `.env` and fill in the required values:
    ```bash
    cp .env.sample .env
    ```
    Note: `SECRET_KEY`, `DATABASE_PASSWORD`, and `CLERK_SECRET_KEY` are mandatory configuration items.

3.  **Database Initialization**:
    ```bash
    docker compose up -d
    ```

4.  **Install Dependencies**:
    ```bash
    # It is recommended to use a virtual environment
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

5.  **Run Migrations**:
    ```bash
    python power_finance/manage.py migrate
    ```

6.  **Start the Development Server**:
    ```bash
    python power_finance/manage.py runserver
    ```

---

## Architecture

The project implements a **Layered Architecture** inspired by Domain-Driven Design (DDD):

*   **Domain Layer**: Core business logic — entities (`Wallet`, `Transaction`, `BalanceCheckpoint`), domain services, and a composable filter-tree DSL.
*   **Application Layer**: Commands, Queries, and Use Cases; idempotency decorator; async use-case base class.
*   **Infrastructure Layer**: Django ORM (PostgreSQL), ImmuDB client (immutable ledger), Redis (cache/throttle), Celery tasks, Clerk integration, repository implementations.
*   **Presentation Layer**: Async DRF views with Redis-sliding-window throttle and idempotency middleware.

### Component Diagram

```mermaid
graph TB
    subgraph presentation["Presentation"]
        API[Async DRF Views<br/>Throttle · Idempotency]
    end

    subgraph application["Application"]
        CMD[Commands]
        QRY[Queries]
        WF[Workflows<br/>webhook delivery]
    end

    subgraph domain["Domain"]
        ENT[Entities<br/>Wallet · Transaction · Checkpoint]
        SVC[Services<br/>apply_transaction · filter_parser]
    end

    subgraph infra["Infrastructure"]
        PG[(PostgreSQL)]
        IMMUDB[(ImmuDB<br/>immutable ledger)]
        REDIS[(Redis<br/>cache · throttle)]
        RMQ[(RabbitMQ)]
        CELERY[Celery Worker<br/>+ Beat]
        CLERK[Clerk SDK]
    end

    API --> CMD & QRY
    CMD & QRY --> ENT & SVC
    CMD & QRY --> PG & IMMUDB & REDIS
    API --> REDIS
    CMD -->|events| RMQ --> CELERY
    CELERY --> IMMUDB
    CELERY -->|webhooks| External[External Services]
    API --> CLERK
```

### Current Implementation: HTTP REST API

The backend currently exposes a RESTful API. All API endpoints require a valid Clerk JWT for authentication, excluding standard administrative interfaces and the documentation UI.

#### Interactive API Documentation
The project uses `drf-spectacular` to generate a comprehensive OpenAPI 3.0 schema. You can explore the API using the built-in Swagger UI:

- **Swagger UI**: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)
- **Schema (Raw)**: [http://localhost:8000/api/schema/](http://localhost:8000/api/schema/)

#### API Endpoints (v1)

| Category | Endpoint | Method | Description |
| :--- | :--- | :--- | :--- |
| **Wallets** | `/api/v1/wallets/` | `GET`, `POST` | List and create wallets |
| | `/api/v1/wallets/{id}/` | `GET`, `PUT`, `PATCH`, `DELETE` | Manage specific wallet resources |
| | `/api/v1/wallets/search/` | `POST` | Advanced filtering for wallets |
| **Transactions** | `/api/v1/transactions/` | `GET`, `POST` | List and create transaction records |
| | `/api/v1/transactions/{id}/` | `GET`, `PUT`, `PATCH`, `DELETE` | Manage specific transaction resources |
| | `/api/v1/transactions/search/` | `POST` | Advanced filtering for ledger entries |
| **Webhooks** | `/api/v1/webhooks/` | `GET`, `POST` | List and register outgoing webhooks |
| | `/api/v1/webhooks/{id}/` | `GET`, `PUT`, `PATCH`, `DELETE` | Manage webhook settings and rotation |
| **Notifications**| `/api/v1/notifications/` | `GET` | List user notifications |
| | `/api/v1/notifications/ack/`| `POST` | Acknowledge individual or batch notifications |
| **Analytics** | `/api/v1/analytics/categories/` | `GET` | Retrieve spending by category |
| | `/api/v1/analytics/money-flow/` | `GET` | Analyze income vs. expense flow |
| | `/api/v1/analytics/expenditure/` | `GET` | Detailed expenditure breakdown |
| | `/api/v1/analytics/spending-heatmap/` | `GET` | Activity heatmap data retrieval |
| | `/api/v1/analytics/wallet-history/` | `GET` | Historical balance data per wallet |

---

## Authentication and Clerk Integration

Identity management is handled by **Clerk**. Authentication is enforced via JWT Bearer tokens.

### Authentication Flow

1.  **Client** authenticates with Clerk and receives a JWT.
2.  **Client** includes the JWT in the `Authorization: Bearer <token>` header of API requests.
3.  **Backend** validates the JWT signature and expiration using Clerk's JWKS (JSON Web Key Sets).
4.  **Backend** extracts the unique `sub` (External User ID) from the token payload.
5.  **Sync Service** synchronizes the external identity with the local database, ensuring the user profile is up-to-date.

```mermaid
sequenceDiagram
    participant Client
    participant Backend
    participant Clerk
    participant Database

    Client->>Clerk: Login / Get JWT
    Clerk-->>Client: JWT Token
    Client->>Backend: API Request (Authorization: Bearer <token>)
    Backend->>Backend: Decode & Validate JWT (via JWKS)
    alt User Profile Missing or Outdated
        Backend->>Clerk: Fetch Extended User Info
        Clerk-->>Backend: User Profile Data
        Backend->>Database: Synchronize Local User Record
    end
    Backend->>Database: Execute Domain Logic
    Database-->>Backend: Data Persistence Result
    Backend-->>Client: API Response (JSON)
```

### Asynchronous Event & Notification Delivery Flow

The system uses an event-driven architecture to handle side effects like webhook deliveries and live notifications without blocking the main request-response cycle.

```mermaid
sequenceDiagram
    participant Client
    participant Backend
    participant Database
    participant Celery as Celery Worker
    participant Webhook as External Webhook
    participant Broker as Notification Broker
    participant Stream as SSE Stream

    Client->>Backend: API Request (e.g. Create Transaction)
    Backend->>Database: Save Record
    Backend->>Celery: Trigger Asynchronous Tasks
    Backend-->>Client: HTTP 201 Created

    rect rgb(240, 240, 240)
        Note over Celery: Background Processing
        Celery->>Webhook: POST Webhook Payload (External)
        Webhook-->>Celery: HTTP 200 OK
        Celery->>Broker: Push Event to User Channel (Internal)
        Broker->>Stream: Forward Event
        Stream-->>Client: SSE Event (Real-time Update)
    end
```

---

## Infrastructure and Observability

The application is fully containerized. Both Docker Compose (local dev) and Kubernetes manifests (`deploy/kubernetes/`) are provided.

### Background Processing
- **Celery & RabbitMQ**: Async event handling — webhook delivery, delivery retries.
- **Celery Beat**: Periodic balance-checkpoint task writes a `BalanceCheckpoint` to ImmuDB, keeping read-model balance queries O(1) instead of full ledger replay.
- **Redis**: Celery result backend, JWT auth cache, and sliding-window rate-limit counters.

### Immutable Transaction Ledger (ImmuDB)
Transactions are appended to ImmuDB — a tamper-evident, cryptographically verified ledger. Wallet balance is **derived state**: `balance = latest_checkpoint.amount + sum(transactions since checkpoint)`. This makes balance history auditable without separate audit-log infrastructure.

```mermaid
flowchart LR
    T1[tx +100] --> T2[tx -30] --> T3[tx +50] --> CP["checkpoint\n120"] --> T4[tx -20]
    CP -->|"balance = 120 + (−20) = 100"| B[current balance]
```

### Kubernetes Deployment
Full manifests in `deploy/kubernetes/`:

| Resource | Description |
|---|---|
| Deployments | `django`, `celery-worker`, `postgres`, `redis`, `rabbitmq` |
| Services | LoadBalancer (django), ClusterIP (postgres, redis, rabbitmq) |
| PVCs | Persistent volumes for postgres, redis, rabbitmq |
| RBAC | Least-privilege ServiceAccounts for django and celery-worker |
| NetworkPolicies | ImmuDB isolated — only reachable from django + celery |
| ConfigMap / Secrets | Env config and credentials separate from images |

### Persistent Logging
- **`logs/debug.log`**: Main HTTP application.
- **`logs/celery-debug.log`**: Worker and beat activity.

Process-aware routing separates logs by execution context across container rebuilds.

---

## Roadmap and Future Enhancements

*   **Subscriptions & Dunning**: State-machine-driven subscription billing with Celery Beat retry logic.
*   **Money Transfers**: Atomic cross-wallet transfers with deadlock-safe locking.
*   **OpenTelemetry**: Distributed tracing for all k8s services.
*   **Cursor Pagination**: Keyset-based pagination for high-volume transaction lists.
*   **Audit Log**: Structured event sourcing on top of the existing ImmuDB ledger.