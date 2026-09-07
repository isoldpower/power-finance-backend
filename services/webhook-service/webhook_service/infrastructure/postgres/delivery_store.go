package postgres

import (
	"context"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"services/webhook-service/webhook_service/types"
)

// DeliveryStore is the durable delivery queue the scheduler drains.
type DeliveryStore struct {
	pool *pgxpool.Pool
}

// NewDeliveryStore builds the store over a pgx pool.
func NewDeliveryStore(pool *pgxpool.Pool) *DeliveryStore {
	return &DeliveryStore{pool: pool}
}

// Enqueue records a pending delivery, treating an already-enqueued event as a no-op.
func (s *DeliveryStore) Enqueue(ctx context.Context, delivery types.Delivery, at time.Time) error {
	_, execErr := s.pool.Exec(
		ctx,
		`INSERT INTO webhook_deliveries
			(id, webhook_id, user_id, user_external_id, event_id, event_type,
			 target_url, payload, status, attempts, secret_version,
			 next_attempt_at, created_at, updated_at)
		 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'pending', 0, $9, $10, $10, $10)
		 ON CONFLICT (webhook_id, event_id) DO NOTHING`,
		delivery.ID,
		delivery.WebhookID,
		delivery.UserID,
		delivery.UserExternalID,
		delivery.EventID,
		delivery.EventType,
		delivery.TargetURL,
		delivery.Payload,
		delivery.SecretVersion,
		at,
	)

	if execErr != nil {
		return fmt.Errorf("postgres: enqueue delivery: %w", execErr)
	}

	return nil
}

// ClaimDue leases due deliveries so no concurrent tick claims the same rows.
func (s *DeliveryStore) ClaimDue(
	ctx context.Context,
	now time.Time,
	lease time.Duration,
	limit int,
) ([]types.Delivery, error) {
	rows, queryErr := s.pool.Query(
		ctx,
		`UPDATE webhook_deliveries
		 SET status = 'in_progress', next_attempt_at = NULL, lease_expires_at = $1, updated_at = $2
		 WHERE id IN (
			SELECT id FROM webhook_deliveries
			WHERE (status IN ('pending', 'retry_scheduled') AND next_attempt_at <= $2)
			   OR (status = 'in_progress' AND lease_expires_at <= $2)
			ORDER BY next_attempt_at NULLS FIRST
			FOR UPDATE SKIP LOCKED
			LIMIT $3
		 )
		 RETURNING id, webhook_id, user_id, user_external_id, event_id, event_type,
			target_url, payload, status, attempts, secret_version`,
		now.Add(lease),
		now,
		limit,
	)
	if queryErr != nil {
		return nil, fmt.Errorf("postgres: claim due deliveries: %w", queryErr)
	}
	defer rows.Close()

	var deliveries []types.Delivery
	for rows.Next() {
		var delivery types.Delivery
		scanErr := rows.Scan(
			&delivery.ID,
			&delivery.WebhookID,
			&delivery.UserID,
			&delivery.UserExternalID,
			&delivery.EventID,
			&delivery.EventType,
			&delivery.TargetURL,
			&delivery.Payload,
			&delivery.Status,
			&delivery.Attempts,
			&delivery.SecretVersion,
		)
		if scanErr != nil {
			return nil, fmt.Errorf("postgres: scan delivery: %w", scanErr)
		}
		deliveries = append(deliveries, delivery)
	}

	return deliveries, rows.Err()
}
