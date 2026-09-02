package postgres

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"services/webhook-service/webhook_service/types"
)

type ConfigStore struct {
	pool *pgxpool.Pool
}

func NewConfigStore(pool *pgxpool.Pool) *ConfigStore {
	return &ConfigStore{pool: pool}
}

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

func (s *ConfigStore) DeleteEndpoint(ctx context.Context, webhookID string) error {
	if _, execErr := s.pool.Exec(ctx, `DELETE FROM webhook_endpoints WHERE id = $1`, webhookID); execErr != nil {
		return fmt.Errorf("postgres: delete endpoint: %w", execErr)
	}

	return nil
}

func (s *ConfigStore) AddSubscription(ctx context.Context, subscription types.WebhookSubscription, at time.Time) error {
	_, execErr := s.pool.Exec(
		ctx,
		`INSERT INTO webhook_subscriptions (id, webhook_id, user_id, event_type, created_at)
		 VALUES ($1, $2, $3, $4, $5)
		 ON CONFLICT (webhook_id, event_type) DO NOTHING`,
		subscription.ID,
		subscription.WebhookID,
		subscription.UserID,
		subscription.EventType,
		at,
	)
	if execErr != nil {
		return fmt.Errorf("postgres: add subscription: %w", execErr)
	}

	return nil
}

func (s *ConfigStore) RemoveSubscription(ctx context.Context, subscriptionID string) error {
	if _, execErr := s.pool.Exec(ctx, `DELETE FROM webhook_subscriptions WHERE id = $1`, subscriptionID); execErr != nil {
		return fmt.Errorf("postgres: remove subscription: %w", execErr)
	}

	return nil
}

// ActiveEndpointsForEvent returns every active endpoint subscribed to the
// given event type for the given user.
func (s *ConfigStore) ActiveEndpointsForEvent(
	ctx context.Context,
	userID int,
	eventType string,
) ([]types.WebhookEndpoint, error) {
	rows, queryErr := s.pool.Query(
		ctx,
		`SELECT e.id, e.user_id, e.user_external_id, e.title, e.url,
				e.secret, e.secret_version, e.is_active
		 FROM webhook_endpoints e
		 JOIN webhook_subscriptions s ON s.webhook_id = e.id
		 WHERE e.user_id = $1 AND e.is_active = TRUE AND s.event_type = $2`,
		userID,
		eventType,
	)
	if queryErr != nil {
		return nil, fmt.Errorf("postgres: query active endpoints: %w", queryErr)
	}
	defer rows.Close()

	var endpoints []types.WebhookEndpoint
	for rows.Next() {
		var endpoint types.WebhookEndpoint
		scanErr := rows.Scan(
			&endpoint.ID,
			&endpoint.UserID,
			&endpoint.UserExternalID,
			&endpoint.Title,
			&endpoint.URL,
			&endpoint.Secret,
			&endpoint.SecretVersion,
			&endpoint.IsActive,
		)
		if scanErr != nil {
			return nil, fmt.Errorf("postgres: scan endpoint: %w", scanErr)
		}
		endpoints = append(endpoints, endpoint)
	}

	return endpoints, rows.Err()
}

func (s *ConfigStore) EndpointSecrets(ctx context.Context, webhookID string) (types.EndpointSecrets, error) {
	var (
		secrets         types.EndpointSecrets
		previousVersion *int
	)
	scanErr := s.pool.
		QueryRow(
			ctx,
			`SELECT secret, secret_version, previous_secret,
					previous_secret_version, previous_secret_expires_at
			 FROM webhook_endpoints WHERE id = $1`,
			webhookID,
		).
		Scan(
			&secrets.Secret,
			&secrets.SecretVersion,
			&secrets.PreviousSecret,
			&previousVersion,
			&secrets.PreviousSecretExpiresAt,
		)
	if errors.Is(scanErr, pgx.ErrNoRows) {
		return types.EndpointSecrets{}, nil
	} else if scanErr != nil {
		return types.EndpointSecrets{}, fmt.Errorf("postgres: endpoint secrets: %w", scanErr)
	}

	if previousVersion != nil {
		secrets.PreviousSecretVersion = *previousVersion
	}

	return secrets, nil
}

// EndpointOwner reports the external user id an endpoint belongs to, or blank
// when it no longer exists.
func (s *ConfigStore) EndpointOwner(ctx context.Context, webhookID string) (string, error) {
	var owner string
	scanErr := s.pool.
		QueryRow(ctx, `SELECT user_external_id FROM webhook_endpoints WHERE id = $1`, webhookID).
		Scan(&owner)
	if errors.Is(scanErr, pgx.ErrNoRows) {
		return "", nil
	} else if scanErr != nil {
		return "", fmt.Errorf("postgres: endpoint owner: %w", scanErr)
	}

	return owner, nil
}
