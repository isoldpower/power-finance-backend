package webhook_service

import (
	"services/webhook-service/webhook_service/infrastructure/kafka"
	"services/webhook-service/webhook_service/infrastructure/postgres"
	httpserver "services/webhook-service/webhook_service/presentation/http"
	"services/webhook-service/webhook_service/services"
)

type Config struct {
	Server   httpserver.Config
	Kafka    kafka.Config
	Postgres postgres.Config
	Delivery services.DeliveryConfig
}
