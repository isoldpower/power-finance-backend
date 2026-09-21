package postgres

import (
	"context"
	"fmt"
	"time"
)

// MarkSucceeded closes a delivery out as delivered and releases its lease.
func (s *DeliveryStore) MarkSucceeded(
	ctx context.Context,
	deliveryID string,
	attempts int,
	at time.Time,
) error {
	_, execErr := s.pool.Exec(
		ctx,
		`UPDATE webhook_deliveries
		 SET status = 'success', attempts = $2, last_error = '',
			 next_attempt_at = NULL, lease_expires_at = NULL, updated_at = $3
		 WHERE id = $1`,
		deliveryID, attempts, at,
	)

	if execErr != nil {
		return fmt.Errorf("postgres: mark delivery succeeded: %w", execErr)
	}

	return nil
}

// MarkFailed closes a delivery out as exhausted, recording the last error.

// MarkFailed closes a delivery out as exhausted, recording the last error.
func (s *DeliveryStore) MarkFailed(
	ctx context.Context,
	deliveryID string,
	attempts int,
	lastError string,
	at time.Time,
) error {
	_, execErr := s.pool.Exec(
		ctx,
		`UPDATE webhook_deliveries
		 SET status = 'failed', attempts = $2, last_error = $3,
			 next_attempt_at = NULL, lease_expires_at = NULL, updated_at = $4
		 WHERE id = $1`,
		deliveryID, attempts, lastError, at,
	)

	if execErr != nil {
		return fmt.Errorf("postgres: mark delivery failed: %w", execErr)
	}

	return nil
}

// Reschedule releases the lease and pushes the next attempt into the future after a retryable failure.

// Reschedule releases the lease and pushes the next attempt into the future after a retryable failure.
func (s *DeliveryStore) Reschedule(
	ctx context.Context,
	deliveryID string,
	attempts int,
	lastError string,
	nextAttemptAt time.Time,
	at time.Time,
) error {
	_, execErr := s.pool.Exec(
		ctx,
		`UPDATE webhook_deliveries
		 SET status = 'retry_scheduled', attempts = $2, last_error = $3,
			 next_attempt_at = $4, lease_expires_at = NULL, updated_at = $5
		 WHERE id = $1`,
		deliveryID, attempts, lastError, nextAttemptAt, at,
	)

	if execErr != nil {
		return fmt.Errorf("postgres: reschedule delivery: %w", execErr)
	}

	return nil
}
