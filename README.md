# Power Finance Backend

A robust financial management backend built with Django, utilizing Domain-Driven Design (DDD) principles and Clean Architecture.

## Features

*   **Wallet Management**: Track multiple wallets and their balances.
*   **Transaction Tracking**: Detailed history of income and expenditures.
*   **Advanced Analytics**: Spending heatmaps, category breakdowns, and money flow analysis.
*   **Secure Authentication**: Integrated with Clerk for JWT-based authentication.
*   **Layered Architecture**: Clean separation between Domain, Application, and Infrastructure layers.

---

## Getting Started

### Prerequisites

*   **Python 3.12+**
*   **Docker & Docker Compose**
*   **PostgreSQL** (Managed via Docker)

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

*   **Domain Layer**: Contains core business logic, entities (Wallet, Transaction), and domain services.
*   **Application Layer**: Orchestrates domain logic via Commands, Queries, and Use Case services.
*   **Infrastructure Layer**: Handles external concerns such as Database persistence (Django ORM), External integrations (Clerk), and Repository implementations.
*   **Presentation Layer**: Responsible for the HTTP interface, including DRF ViewSets and API routing.

### Current Implementation: HTTP REST API

The backend currently exposes a RESTful API. All API endpoints require a valid Clerk JWT for authentication, excluding standard administrative interfaces.

#### API Endpoints (v1)

| Category | Endpoint | Method | Description |
| :--- | :--- | :--- | :--- |
| **Wallets** | `/api/v1/wallets/` | `GET`, `POST` | List and create wallets |
| | `/api/v1/wallets/{id}/` | `GET`, `PUT`, `PATCH`, `DELETE` | Manage specific wallet resources |
| **Transactions** | `/api/v1/transactions/` | `GET`, `POST` | List and create transaction records |
| | `/api/v1/transactions/{id}/` | `GET`, `PUT`, `PATCH`, `DELETE` | Manage specific transaction resources |
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

---

## Roadmap and Future Enhancements

*   **Swagger UI Integration**: Implementation of OpenAPI specifications for interactive API documentation and testing.
*   **WebSockets**: Real-time event streaming for balance updates and transaction notifications.
*   **Webhook Support**: Native handling for external system events (e.g., Clerk user events, payment notifications).
*   **Ledger-based Accounting**: Transition to a double-entry ledger system for enhanced financial auditing and integrity.
*   **Unified Business Logic Flow**: Further refinement of the interaction patterns between the REST interface and application services.