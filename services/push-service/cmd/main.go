package main

import (
	"log/slog"
	"os"

	"services/push-service/cmd/config"
	"services/push-service/internal/logging"
	"services/push-service/push_service"
)

func main() {
	logging.Setup()

	if startErr := push_service.StartPushService(config.Load()); startErr != nil {
		slog.Error("push service failed to start", "error", startErr)
		os.Exit(1)
	}
}
