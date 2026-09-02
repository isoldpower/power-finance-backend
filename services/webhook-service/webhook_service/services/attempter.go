package services

import (
	"context"
	"log/slog"
	"strconv"
	"time"

	"services/webhook-service/internal/metrics"
	"services/webhook-service/webhook_service/types"
)

type deliveryStore interface {
	Enqueue(ctx context.Context, delivery types.Delivery, at time.Time) error
	ClaimDue(ctx context.Context, now time.Time, lease time.Duration, limit int) ([]types.Delivery, error)
	MarkSucceeded(ctx context.Context, deliveryID string, attempts int, at time.Time) error
	MarkFailed(ctx context.Context, deliveryID string, attempts int, lastError string, at time.Time) error
	Reschedule(ctx context.Context, deliveryID string, attempts int, lastError string, nextAttemptAt time.Time, at time.Time) error
}

type secretResolver interface {
	EndpointSecrets(ctx context.Context, webhookID string) (types.EndpointSecrets, error)
}

type sender interface {
	Send(ctx context.Context, delivery types.Delivery, secret string, at time.Time) error
}

type notifier interface {
	RequestNotification(ctx context.Context, delivery types.Delivery, short, message string) error
}

type DeliveryAttempter struct {
	deliveries   deliveryStore
	secrets      secretResolver
	sender       sender
	notifier     notifier
	maxAttempts  int
	retryBackoff time.Duration
}

func NewDeliveryAttempter(
	deliveries deliveryStore,
	secrets secretResolver,
	sender sender,
	notifier notifier,
	maxAttempts int,
	retryBackoff time.Duration,
) *DeliveryAttempter {
	return &DeliveryAttempter{
		deliveries:   deliveries,
		secrets:      secrets,
		sender:       sender,
		notifier:     notifier,
		maxAttempts:  maxAttempts,
		retryBackoff: retryBackoff,
	}
}

// Attempt performs one delivery try; an empty secret is resolved from the
// store (e.g. a scheduler-claimed redelivery).
func (a *DeliveryAttempter) Attempt(ctx context.Context, delivery types.Delivery, secret string) error {
	now := time.Now().UTC()
	attemptNumber := delivery.Attempts + 1

	if secret == "" {
		resolved, secretErr := a.secrets.EndpointSecrets(ctx, delivery.WebhookID)
		if secretErr != nil {
			return secretErr
		}
		secret = resolved.For(delivery.SecretVersion, now)
	}

	metrics.DeliveryAttempted()
	sendStart := time.Now()
	sendErr := a.sender.Send(ctx, delivery, secret, now)
	metrics.ObserveAttemptDuration(time.Since(sendStart).Seconds())
	if sendErr == nil {
		return a.recordSuccess(ctx, delivery, attemptNumber, now)
	}

	if attemptNumber >= a.maxAttempts {
		return a.recordFailure(ctx, delivery, attemptNumber, sendErr.Error(), now)
	}

	metrics.DeliveryOutcome(metrics.OutcomeRetry)
	nextAttemptAt := now.Add(a.retryBackoff * time.Duration(attemptNumber))
	slog.Warn(
		"webhook delivery failed, rescheduling",
		"delivery_id", delivery.ID,
		"attempt", attemptNumber,
		"next_attempt_at", nextAttemptAt,
		"error", sendErr,
	)

	return a.deliveries.Reschedule(ctx, delivery.ID, attemptNumber, sendErr.Error(), nextAttemptAt, now)
}

func (a *DeliveryAttempter) recordSuccess(ctx context.Context, delivery types.Delivery, attempts int, now time.Time) error {
	if markErr := a.deliveries.MarkSucceeded(ctx, delivery.ID, attempts, now); markErr != nil {
		return markErr
	}

	metrics.DeliveryOutcome(metrics.OutcomeSuccess)
	slog.Info("webhook delivered", "delivery_id", delivery.ID, "attempts", attempts)
	a.requestNotification(
		ctx,
		delivery,
		"Webhook delivered",
		"Your webhook received the "+delivery.EventType+" event.",
	)

	return nil
}

func (a *DeliveryAttempter) recordFailure(ctx context.Context, delivery types.Delivery, attempts int, lastError string, now time.Time) error {
	if markErr := a.deliveries.MarkFailed(ctx, delivery.ID, attempts, lastError, now); markErr != nil {
		return markErr
	}

	metrics.DeliveryOutcome(metrics.OutcomeExhausted)
	slog.Error("webhook delivery exhausted retries", "delivery_id", delivery.ID, "attempts", attempts)
	a.requestNotification(
		ctx,
		delivery,
		"Webhook delivery failed",
		"Your webhook for the "+delivery.EventType+" event could not be delivered after "+
			strconv.Itoa(attempts)+" attempts.",
	)

	return nil
}

func (a *DeliveryAttempter) requestNotification(ctx context.Context, delivery types.Delivery, short, message string) {
	if notifyErr := a.notifier.RequestNotification(ctx, delivery, short, message); notifyErr != nil {
		slog.Error("failed to request delivery notification", "delivery_id", delivery.ID, "error", notifyErr)
	}
}
