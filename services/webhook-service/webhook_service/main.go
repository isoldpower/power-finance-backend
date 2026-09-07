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

// StartWebhookService wires the service and blocks until shutdown, failing fast on a wiring error.
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
	schedulerDone := handler.Start(rootContext)

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
	defer consumer.Close()

	consumerDone := make(chan struct{})
	go func() {
		defer close(consumerDone)
		consumer.Run(rootContext)
	}()

	deliveryLog := services.NewDeliveryLogService(stores.DeliveryLogStore, stores.ConfigStore)
	httpserver.
		NewServer(serviceConfig.Server, readinessProbe, deliveryLog).
		Run(rootContext)

	awaitBackgroundDrainBeforeCleanup(consumerDone, schedulerDone)

	return nil
}

func awaitBackgroundDrainBeforeCleanup(consumerDone, schedulerDone <-chan struct{}) {
	<-consumerDone
	<-schedulerDone
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
	scheduler := services.NewRetryScheduler(
		stores.DeliveryStore,
		attempter,
		deliveryConfig.SchedulerInterval,
	)
	dispatcher := services.NewDeliveryDispatcher(
		stores.ConfigStore,
		stores.DeliveryStore,
		scheduler,
	)
	configProjection := services.NewConfigProjection(stores.ConfigStore)

	return handlers.NewWebhookHandler(configProjection, dispatcher, scheduler)
}
