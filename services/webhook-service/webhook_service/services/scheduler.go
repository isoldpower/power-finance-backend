package services

import (
	"context"
	"log/slog"
	"time"

	"services/webhook-service/webhook_service/types"
)

const (
	scheduledBatchSize = 100
	claimLease         = 5 * time.Minute
)

type RetryScheduler struct {
	deliveries deliveryStore
	attempter  deliveryAttempter
	interval   time.Duration
}

func NewRetryScheduler(
	deliveries deliveryStore,
	attempter deliveryAttempter,
	interval time.Duration,
) *RetryScheduler {
	return &RetryScheduler{
		deliveries: deliveries,
		attempter:  attempter,
		interval:   interval,
	}
}

// Run blocks until the context is cancelled, ticking on the configured interval.
func (s *RetryScheduler) Run(ctx context.Context) {
	ticker := time.NewTicker(s.interval)
	defer ticker.Stop()
	slog.Info("webhook retry scheduler started", "interval", s.interval)

	for {
		select {
		case <-ctx.Done():
			slog.Info("webhook retry scheduler stopped")
			return
		case <-ticker.C:
			s.runOnce(ctx)
		}
	}
}

func (s *RetryScheduler) runOnce(ctx context.Context) {
	now := time.Now().UTC()
	due, claimErr := s.deliveries.ClaimDue(ctx, now, claimLease, scheduledBatchSize)
	if claimErr != nil {
		slog.Error("retry scheduler: claim due deliveries failed", "error", claimErr)
		return
	}

	for _, delivery := range due {
		if ctx.Err() != nil {
			return
		}
		s.attempt(ctx, delivery)
	}
}

func (s *RetryScheduler) attempt(ctx context.Context, delivery types.Delivery) {
	if attemptErr := s.attempter.Attempt(ctx, delivery, ""); attemptErr != nil {
		slog.Error(
			"retry scheduler: attempt bookkeeping failed",
			"delivery_id",
			delivery.ID,
			"error",
			attemptErr,
		)
	}
}
