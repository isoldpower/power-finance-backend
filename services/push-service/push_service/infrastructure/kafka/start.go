package kafka

import (
	"context"

	"services/push-service/internal/log"
	"services/push-service/push_service/services"
)

func StartKafkaConsumer(ctx context.Context, eventsSink chan<- services.OutboxEvent) {
	consumerConfig := LoadConsumerConfigFromEnv()

	consumerLoop, buildErr := BuildNotificationsConsumerLoop(ctx, consumerConfig, eventsSink)
	if buildErr != nil {
		log.PrintError(
			"Kafka consumer disabled: failed to connect; SSE will serve heartbeats only",
			buildErr,
		)
		return
	}

	go consumerLoop.Run(ctx)
}
