package main

import (
	"log/slog"
	"os"

	"services/webhook-service/cmd/config"
	"services/webhook-service/internal/logging"
	"services/webhook-service/webhook_service"
)

func main() {
	logging.Setup()

	if startErr := webhook_service.StartWebhookService(config.Load()); startErr != nil {
		slog.Error("webhook service failed to start", "error", startErr)
		os.Exit(1)
	}
}
