-- +goose Up
-- +goose StatementBegin
CREATE TABLE webhook_endpoints (
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

CREATE TABLE webhook_subscriptions (
    id         UUID PRIMARY KEY,
    webhook_id UUID NOT NULL REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
    user_id    BIGINT NOT NULL,
    event_type TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (webhook_id, event_type)
);

CREATE INDEX webhook_subscriptions_event_type_idx
    ON webhook_subscriptions (event_type);

CREATE TABLE webhook_deliveries (
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

CREATE INDEX webhook_deliveries_due_idx
    ON webhook_deliveries (status, next_attempt_at);

CREATE TABLE kafka_consumed_events (
    consumer_group TEXT NOT NULL,
    event_id       TEXT NOT NULL,
    consumed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (consumer_group, event_id)
);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
DROP TABLE kafka_consumed_events;
DROP TABLE webhook_deliveries;
DROP TABLE webhook_subscriptions;
DROP TABLE webhook_endpoints;
-- +goose StatementEnd
