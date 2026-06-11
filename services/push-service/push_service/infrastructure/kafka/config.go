package kafka

import (
	"os"
	"strings"

	"github.com/power-finance/kafka-client-go/publisher"
)

const (
	defaultBootstrapServers = "localhost:9092"
	defaultOutboxTopic      = "events.async"
	defaultGroupID          = "push-service.notifications"
	clientID                = "push-service"
)

type ConsumerConfig struct {
	BootstrapServers string
	GroupID          string
	Topics           []string
	RetryTopic       string
	DLQTopic         string
}

func LoadConsumerConfigFromEnv() ConsumerConfig {
	return ConsumerConfig{
		BootstrapServers: envOrDefault("KAFKA_BOOTSTRAP_SERVERS", defaultBootstrapServers),
		GroupID:          envOrDefault("KAFKA_PUSH_GROUP_ID", defaultGroupID),
		Topics:           splitTopics(envOrDefault("KAFKA_OUTBOX_TOPIC", defaultOutboxTopic)),
		RetryTopic:       envOrDefault("KAFKA_RETRY_TOPIC", publisher.DefaultRetryTopic),
		DLQTopic:         envOrDefault("KAFKA_DLQ_TOPIC", publisher.DefaultDLQTopic),
	}
}

func envOrDefault(name string, defaultValue string) string {
	if value := os.Getenv(name); value != "" {
		return value
	}

	return defaultValue
}

func splitTopics(commaSeparatedTopics string) []string {
	rawTopics := strings.Split(commaSeparatedTopics, ",")

	topics := make([]string, 0, len(rawTopics))
	for _, rawTopic := range rawTopics {
		if topic := strings.TrimSpace(rawTopic); topic != "" {
			topics = append(topics, topic)
		}
	}

	return topics
}
