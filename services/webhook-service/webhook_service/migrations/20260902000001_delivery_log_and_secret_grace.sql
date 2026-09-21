-- +goose Up
-- +goose StatementBegin

-- Two secrets are live during a rotation's 24h grace window. A delivery
-- records which one signed it, so rotating does not orphan an in-flight
-- delivery the receiver is still prepared to verify.
ALTER TABLE webhook_endpoints
    ADD COLUMN IF NOT EXISTS secret_version INT NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS previous_secret TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS previous_secret_version INT,
    ADD COLUMN IF NOT EXISTS previous_secret_expires_at TIMESTAMPTZ;

ALTER TABLE webhook_deliveries
    ADD COLUMN IF NOT EXISTS secret_version INT NOT NULL DEFAULT 1,
    -- The claim lease. Split from next_attempt_at because the delivery log
    -- reports next_attempt_at to users and a lease deadline is not one.
    ADD COLUMN IF NOT EXISTS lease_expires_at TIMESTAMPTZ;

-- A finished delivery has nothing scheduled.
ALTER TABLE webhook_deliveries
    ALTER COLUMN next_attempt_at DROP NOT NULL;

UPDATE webhook_deliveries
   SET next_attempt_at = NULL
 WHERE status IN ('success', 'failed');

DROP INDEX IF EXISTS webhook_deliveries_due_idx;

CREATE INDEX IF NOT EXISTS webhook_deliveries_due_idx
    ON webhook_deliveries (status, next_attempt_at)
 WHERE status IN ('pending', 'retry_scheduled');

CREATE INDEX IF NOT EXISTS webhook_deliveries_lease_idx
    ON webhook_deliveries (lease_expires_at)
 WHERE status = 'in_progress';

-- The delivery log's keyset order, scoped to one endpoint.
CREATE INDEX IF NOT EXISTS webhook_deliveries_log_idx
    ON webhook_deliveries (webhook_id, created_at DESC, id DESC);

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
DROP INDEX IF EXISTS webhook_deliveries_log_idx;
DROP INDEX IF EXISTS webhook_deliveries_lease_idx;
DROP INDEX IF EXISTS webhook_deliveries_due_idx;

CREATE INDEX IF NOT EXISTS webhook_deliveries_due_idx
    ON webhook_deliveries (status, next_attempt_at);

UPDATE webhook_deliveries SET next_attempt_at = now() WHERE next_attempt_at IS NULL;

ALTER TABLE webhook_deliveries
    ALTER COLUMN next_attempt_at SET NOT NULL;

ALTER TABLE webhook_deliveries
    DROP COLUMN IF EXISTS lease_expires_at,
    DROP COLUMN IF EXISTS secret_version;

ALTER TABLE webhook_endpoints
    DROP COLUMN IF EXISTS previous_secret_expires_at,
    DROP COLUMN IF EXISTS previous_secret_version,
    DROP COLUMN IF EXISTS previous_secret,
    DROP COLUMN IF EXISTS secret_version;
-- +goose StatementEnd
