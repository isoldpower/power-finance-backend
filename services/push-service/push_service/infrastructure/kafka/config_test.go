package kafka

import (
	"testing"
)

func TestConfigDefaults(t *testing.T) {
	config := LoadConsumerConfigFromEnv()

	if config.BootstrapServers != "localhost:9092" {
		t.Fatalf("expected default bootstrap servers, got %q", config.BootstrapServers)
	}
	if config.GroupID != "push-service.notifications" {
		t.Fatalf("expected default group id, got %q", config.GroupID)
	}
	if len(config.Topics) != 1 || config.Topics[0] != "events.async" {
		t.Fatalf("expected default topic events.async, got %v", config.Topics)
	}
	if config.RetryTopic != "events.retry" || config.DLQTopic != "events.dlq" {
		t.Fatalf("expected library default failure topics, got %q/%q", config.RetryTopic, config.DLQTopic)
	}
}

func TestConfigReadsEnvironmentOverrides(t *testing.T) {
	t.Setenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
	t.Setenv("KAFKA_PUSH_GROUP_ID", "push-service.staging")
	t.Setenv("KAFKA_OUTBOX_TOPIC", "events.async, events.audit")
	t.Setenv("KAFKA_RETRY_TOPIC", "events.retry.v2")
	t.Setenv("KAFKA_DLQ_TOPIC", "events.dlq.v2")

	config := LoadConsumerConfigFromEnv()

	if config.BootstrapServers != "kafka:9092" {
		t.Fatalf("expected kafka:9092, got %q", config.BootstrapServers)
	}
	if config.GroupID != "push-service.staging" {
		t.Fatalf("expected push-service.staging, got %q", config.GroupID)
	}
	if len(config.Topics) != 2 || config.Topics[0] != "events.async" || config.Topics[1] != "events.audit" {
		t.Fatalf("expected two trimmed topics, got %v", config.Topics)
	}
	if config.RetryTopic != "events.retry.v2" || config.DLQTopic != "events.dlq.v2" {
		t.Fatalf("expected overridden failure topics, got %q/%q", config.RetryTopic, config.DLQTopic)
	}
}

func TestSplitTopicsDropsEmptyEntries(t *testing.T) {
	topics := splitTopics("events.async,, ,events.audit,")

	if len(topics) != 2 {
		t.Fatalf("expected 2 topics, got %v", topics)
	}
}
