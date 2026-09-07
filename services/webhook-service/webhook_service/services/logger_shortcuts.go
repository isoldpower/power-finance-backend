package services

import (
	"log/slog"
	"time"
)

func logEndpointProjected(webhookID string) {
	slog.Debug("projected webhook endpoint created", "webhook_id", webhookID)
}

func logSchedulerStarted(interval time.Duration) {
	slog.Info("webhook retry scheduler started", "interval", interval)
}

func logSchedulerStopped() {
	slog.Info("webhook retry scheduler stopped")
}

func logClaimDueFailed(err error) {
	slog.Error("retry scheduler: claim due deliveries failed", "error", err)
}

func logAttemptBookkeepingFailed(deliveryID string, err error) {
	slog.Error("retry scheduler: attempt bookkeeping failed", "delivery_id", deliveryID, "error", err)
}

func logDeliveryRescheduled(deliveryID string, attempt int, nextAttemptAt time.Time, err error) {
	slog.Warn(
		"webhook delivery failed, rescheduling",
		"delivery_id", deliveryID,
		"attempt", attempt,
		"next_attempt_at", nextAttemptAt,
		"error", err,
	)
}

func logDeliverySucceeded(deliveryID string, attempts int) {
	slog.Info("webhook delivered", "delivery_id", deliveryID, "attempts", attempts)
}

func logDeliveryExhausted(deliveryID string, attempts int) {
	slog.Error("webhook delivery exhausted retries", "delivery_id", deliveryID, "attempts", attempts)
}

func logNotificationRequestFailed(deliveryID string, err error) {
	slog.Error("failed to request delivery notification", "delivery_id", deliveryID, "error", err)
}
