package postgres

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"

	"services/webhook-service/webhook_service/types"
)

// AddSubscription subscribes an endpoint to one event type.
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

// RemoveSubscription drops one subscription by id.

// RemoveSubscription drops one subscription by id.
func (s *ConfigStore) RemoveSubscription(ctx context.Context, subscriptionID string) error {
	const statement = `DELETE FROM webhook_subscriptions WHERE id = $1`

	if _, execErr := s.pool.Exec(ctx, statement, subscriptionID); execErr != nil {
		return fmt.Errorf("postgres: remove subscription: %w", execErr)
	}

	return nil
}

// ActiveEndpointsForEvent returns every active endpoint subscribed to the given event type for the given user.

// ActiveEndpointsForEvent returns every active endpoint subscribed to the given event type for the given user.
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

// EndpointSecrets returns the secrets an endpoint may currently sign with.

// EndpointSecrets returns the secrets an endpoint may currently sign with.
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

// EndpointOwner reports the external user id an endpoint belongs to, or blank when it no longer exists.

// EndpointOwner reports the external user id an endpoint belongs to, or blank when it no longer exists.
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
