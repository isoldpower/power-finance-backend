package webhook_service

import (
	"services/webhook-service/internal/health"
	"services/webhook-service/internal/signals"
	"services/webhook-service/webhook_service/handlers"
	"services/webhook-service/webhook_service/infrastructure/kafka"
	"services/webhook-service/webhook_service/infrastructure/postgres"
	httpserver "services/webhook-service/webhook_service/presentation/http"
	"services/webhook-service/webhook_service/services"
)

// StartWebhookService wires the service and blocks until shutdown; wiring errors
// fail fast so the readiness probe never flips green on a half-built service.
func StartWebhookService(serviceConfig Config) error {
	rootContext, stop := signals.NotifyContext()
	defer stop()

	stores, closeStores, postgresErr := postgres.Bootstrap(
		rootContext,
		serviceConfig.Postgres,
		serviceConfig.Kafka.GroupID,
	)
	if postgresErr != nil {
		return postgresErr
	}
	defer closeStores()

	producer, producerErr := kafka.StartProducer(rootContext, serviceConfig.Kafka)
	if producerErr != nil {
		return producerErr
	}
	defer producer.Stop()

	handler := buildHandler(producer, stores, serviceConfig.Delivery)
	handler.Start(rootContext)

	readinessProbe := health.NewProbe()
	consumer, consumerErr := kafka.NewConsumer(
		rootContext,
		serviceConfig.Kafka,
		stores.DedupeStore,
		handler,
		readinessProbe,
	)
	if consumerErr != nil {
		return consumerErr
	}

	go consumer.Run(rootContext)
	httpserver.NewServer(serviceConfig.Server, readinessProbe).
		Run(rootContext)

	return nil
}

func buildHandler(
	producer *kafka.Producer,
	stores *postgres.Stores,
	deliveryConfig services.DeliveryConfig,
) *handlers.WebhookHandler {
	attempter := services.NewDeliveryAttempter(
		stores.DeliveryStore,
		stores.ConfigStore,
		services.NewHTTPSender(deliveryConfig.Timeout),
		producer,
		deliveryConfig.MaxAttempts,
		deliveryConfig.RetryBackoff,
	)
	dispatcher := services.NewDeliveryDispatcher(
		stores.ConfigStore,
		stores.DeliveryStore,
		attempter,
	)
	configProjection := services.NewConfigProjection(stores.ConfigStore)
	scheduler := services.NewRetryScheduler(
		stores.DeliveryStore,
		attempter,
		deliveryConfig.SchedulerInterval,
	)

	return handlers.NewWebhookHandler(configProjection, dispatcher, scheduler)
}
