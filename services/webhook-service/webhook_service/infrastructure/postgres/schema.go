package postgres

import (
	"context"
	"fmt"

	"github.com/jackc/pgx/v5/pgxpool"
)

const schemaSQL = `
CREATE TABLE IF NOT EXISTS webhook_endpoints (
    id               UUID PRIMARY KEY,
    user_id          BIGINT NOT NULL,
    user_external_id TEXT NOT NULL DEFAULT '',
    title            TEXT NOT NULL,
    url              TEXT NOT NULL,
    secret           TEXT NOT NULL,
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS webhook_subscriptions (
    id         UUID PRIMARY KEY,
    webhook_id UUID NOT NULL REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
    user_id    BIGINT NOT NULL,
    event_type TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (webhook_id, event_type)
);

CREATE INDEX IF NOT EXISTS webhook_subscriptions_event_type_idx
    ON webhook_subscriptions (event_type);

CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id               UUID PRIMARY KEY,
    webhook_id       UUID NOT NULL,
    user_id          BIGINT NOT NULL,
    user_external_id TEXT NOT NULL DEFAULT '',
    event_id         TEXT NOT NULL,
    event_type       TEXT NOT NULL,
    target_url       TEXT NOT NULL,
    payload          BYTEA NOT NULL,
    status           TEXT NOT NULL DEFAULT 'pending',
    attempts         INT NOT NULL DEFAULT 0,
    next_attempt_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_error       TEXT NOT NULL DEFAULT '',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (webhook_id, event_id)
);

CREATE INDEX IF NOT EXISTS webhook_deliveries_due_idx
    ON webhook_deliveries (status, next_attempt_at);

CREATE TABLE IF NOT EXISTS kafka_consumed_events (
    consumer_group TEXT NOT NULL,
    event_id       TEXT NOT NULL,
    consumed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (consumer_group, event_id)
);
`

// EnsureSchema applies the table definitions idempotently.
func EnsureSchema(ctx context.Context, pool *pgxpool.Pool) error {
	if _, execErr := pool.Exec(ctx, schemaSQL); execErr != nil {
		return fmt.Errorf("postgres: ensure schema: %w", execErr)
	}

	return nil
}
