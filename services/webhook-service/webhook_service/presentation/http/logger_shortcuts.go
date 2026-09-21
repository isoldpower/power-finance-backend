package http

import "log/slog"

func logServerListening(address string) {
	slog.Info("http server listening", "addr", address)
}

func logListenerServeFailed(err error) {
	slog.Error("http listener serve failed", "error", err)
}

func logServerShutdownFailed(err error) {
	slog.Error("http server shutdown failed", "error", err)
}

func logDeliveryLogQueryFailed(webhookID string, err error) {
	slog.Error("delivery log query failed", "webhook_id", webhookID, "error", err)
}
