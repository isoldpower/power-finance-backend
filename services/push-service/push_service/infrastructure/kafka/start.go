package kafka

import (
	"context"

	"services/push-service/internal/health"
	"services/push-service/push_service/types"
)

// StartKafkaConsumer runs a consumer that receives messages from Kafka partitions and
// fans them out to Go channels.
func StartKafkaConsumer(
	ctx context.Context,
	kafkaConfig types.KafkaConfig,
	eventsSink chan<- types.OutboxEvent,
	readinessProbe *health.Probe,
) error {
	consumerLoop, buildErr := BuildNotificationsConsumerLoop(ctx, kafkaConfig, eventsSink, readinessProbe)
	if buildErr != nil {
		return buildErr
	}

	go consumerLoop.Run(ctx)

	return nil
}
