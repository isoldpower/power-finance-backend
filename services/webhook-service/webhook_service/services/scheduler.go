package services

import (
	"context"
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

// RetryScheduler drains due deliveries on a tick and on demand.
type RetryScheduler struct {
	deliveries deliveryStore
	attempter  deliveryAttempter
	interval   time.Duration
	wake       chan struct{}
}

// NewRetryScheduler wires the scheduler over its delivery store and attempter.
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

// Wake asks the scheduler to run a delivery pass promptly.
func (s *RetryScheduler) Wake() {
	select {
	case s.wake <- struct{}{}:
	default:
	}
}

// Run drains due deliveries on each tick and on wake, until the context is cancelled.
func (s *RetryScheduler) Run(ctx context.Context) {
	ticker := time.NewTicker(s.interval)
	defer ticker.Stop()
	logSchedulerStarted(s.interval)

	for {
		select {
		case <-ctx.Done():
			logSchedulerStopped()
			return
		case <-ticker.C:
			s.runOnce(ctx)
		case <-s.wake:
			s.runOnce(ctx)
		}
	}
}

func (s *RetryScheduler) runOnce(ctx context.Context) {
	for {
		if ctx.Err() != nil {
			return
		}

		now := time.Now().UTC()
		due, claimErr := s.deliveries.ClaimDue(ctx, now, claimLease, scheduledBatchSize)
		if claimErr != nil {
			logClaimDueFailed(claimErr)
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
		logAttemptBookkeepingFailed(delivery.ID, attemptErr)
	}
}
