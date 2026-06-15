package kafka

import "context"

// StartProducer builds the notification producer and opens its broker
// connection, failing fast on a wiring error.
func StartProducer(ctx context.Context, config Config) (*Producer, error) {
	producer := NewProducer(config.BootstrapServers, config.NotificationsInboundTopic)
	if startErr := producer.Start(ctx); startErr != nil {
		return nil, startErr
	}

	return producer, nil
}
