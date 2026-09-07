package postgres

import (
	"context"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"services/webhook-service/webhook_service/types"
)

// ConfigStore is the projected endpoint and subscription configuration.
type ConfigStore struct {
	pool *pgxpool.Pool
}

// NewConfigStore builds the store over a pgx pool.
func NewConfigStore(pool *pgxpool.Pool) *ConfigStore {
	return &ConfigStore{pool: pool}
}

// UpsertEndpoint projects a created endpoint, ignoring an event already applied.
func (s *ConfigStore) UpsertEndpoint(ctx context.Context, endpoint types.WebhookEndpoint, at time.Time) error {
	_, execErr := s.pool.Exec(
		ctx,
		`INSERT INTO webhook_endpoints
			(id, user_id, user_external_id, title, url, secret, secret_version,
			 is_active, created_at, updated_at)
		 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $9)
		 ON CONFLICT (id) DO UPDATE SET
			title = EXCLUDED.title,
			url = EXCLUDED.url,
			secret = EXCLUDED.secret,
			secret_version = EXCLUDED.secret_version,
			is_active = EXCLUDED.is_active,
			user_external_id = EXCLUDED.user_external_id,
			updated_at = EXCLUDED.updated_at`,
		endpoint.ID,
		endpoint.UserID,
		endpoint.UserExternalID,
		endpoint.Title,
		endpoint.URL,
		endpoint.Secret,
		endpoint.SecretVersion,
		endpoint.IsActive,
		at,
	)

	if execErr != nil {
		return fmt.Errorf("postgres: upsert endpoint: %w", execErr)
	}

	return nil
}

// UpdateEndpoint projects a title, url or enabled change onto an existing endpoint.
func (s *ConfigStore) UpdateEndpoint(
	ctx context.Context,
	webhookID, title, url string,
	enabled bool,
	at time.Time,
) error {
	_, execErr := s.pool.Exec(
		ctx,
		`UPDATE webhook_endpoints
		 SET title = $2, url = $3, is_active = $4, updated_at = $5
		 WHERE id = $1`,
		webhookID, title, url, enabled, at,
	)
	if execErr != nil {
		return fmt.Errorf("postgres: update endpoint: %w", execErr)
	}

	return nil
}

// RotateSecret installs a new signing secret and dates the one it replaced.
func (s *ConfigStore) RotateSecret(ctx context.Context, rotation types.SecretRotation, at time.Time) error {
	_, execErr := s.pool.Exec(
		ctx,
		`UPDATE webhook_endpoints
		 SET secret = $2,
			 secret_version = $3,
			 previous_secret = $4,
			 previous_secret_version = $5,
			 previous_secret_expires_at = $6,
			 updated_at = $7
		 WHERE id = $1`,
		rotation.WebhookID,
		rotation.Secret,
		rotation.SecretVersion,
		rotation.PreviousSecret,
		rotation.PreviousSecretVersion,
		rotation.PreviousSecretExpiresAt,
		at,
	)
	if execErr != nil {
		return fmt.Errorf("postgres: rotate secret: %w", execErr)
	}

	return nil
}

// DeleteEndpoint removes an endpoint and, by cascade, its subscriptions.
func (s *ConfigStore) DeleteEndpoint(ctx context.Context, webhookID string) error {
	if _, execErr := s.pool.Exec(ctx, `DELETE FROM webhook_endpoints WHERE id = $1`, webhookID); execErr != nil {
		return fmt.Errorf("postgres: delete endpoint: %w", execErr)
	}

	return nil
}
