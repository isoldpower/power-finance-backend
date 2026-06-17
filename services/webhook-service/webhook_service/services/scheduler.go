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

type deliveryAttempter interface {
	Attempt(ctx context.Context, delivery types.Delivery, secret string) error
}

type RetryScheduler struct {
	deliveries deliveryStore
	attempter  deliveryAttempter
	interval   time.Duration
	wake       chan struct{}
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
		wake:       make(chan struct{}, 1),
	}
}

// Wake asks the scheduler to run a delivery pass promptly. It coalesces with any
// already-pending wake and never blocks, so dispatch stays off the hot path.
func (s *RetryScheduler) Wake() {
	select {
	case s.wake <- struct{}{}:
	default:
	}
}

// Run blocks until the context is cancelled, draining due deliveries on each
// tick and whenever woken by a freshly dispatched delivery.
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
		case <-s.wake:
			s.runOnce(ctx)
		}
	}
}

// runOnce drains every currently-due delivery in batches, so a single wake or
// tick fully catches up rather than leaving a backlog for the next one.
func (s *RetryScheduler) runOnce(ctx context.Context) {
	for {
		if ctx.Err() != nil {
			return
		}

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

		if len(due) < scheduledBatchSize {
			return
		}
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
