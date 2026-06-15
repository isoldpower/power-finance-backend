package config

import (
	"log/slog"
	"os"
	"strings"
	"time"

	"github.com/spf13/viper"

	"services/webhook-service/webhook_service"
	"services/webhook-service/webhook_service/infrastructure/kafka"
	"services/webhook-service/webhook_service/infrastructure/postgres"
	httpserver "services/webhook-service/webhook_service/presentation/http"
	"services/webhook-service/webhook_service/services"
)

const (
	configPathVariable = "WEBHOOK_SERVICE_CONFIG_FILE"
	defaultConfigPath  = "./config.yaml"

	serverHostKey = "webhook_service.host"
	serverPortKey = "webhook_service.port"

	bootstrapServersKey          = "kafka.bootstrap_servers"
	outboxTopicKey               = "kafka.outbox_topic"
	groupIDKey                   = "kafka.group_id"
	retryTopicKey                = "kafka.retry_topic"
	dlqTopicKey                  = "kafka.dlq_topic"
	notificationsInboundTopicKey = "kafka.notifications_inbound_topic"

	postgresDSNKey = "postgres.dsn"

	deliveryTimeoutKey           = "delivery.timeout_seconds"
	deliveryMaxAttemptsKey       = "delivery.max_attempts"
	deliveryRetryBackoffKey      = "delivery.retry_backoff_seconds"
	deliverySchedulerIntervalKey = "delivery.scheduler_interval_seconds"
)

// Load resolves and composes all the Viper-based project configurations.
func Load() webhook_service.Config {
	viperInstance := viper.New()
	registerDefaults(viperInstance)

	configPath := resolveConfigPath()
	ResolveViper(viperInstance, configPath)
	if resolveErr := TryResolveConfig(viperInstance); resolveErr != nil {
		slog.Warn("failed to read config file", "path", configPath, "error", resolveErr)
	}

	return webhook_service.Config{
		Server: httpserver.Config{
			Host: viperInstance.GetString(serverHostKey),
			Port: viperInstance.GetInt(serverPortKey),
		},
		Kafka: kafka.Config{
			BootstrapServers:          viperInstance.GetString(bootstrapServersKey),
			OutboxTopics:              splitTopics(viperInstance.GetString(outboxTopicKey)),
			GroupID:                   viperInstance.GetString(groupIDKey),
			RetryTopic:                viperInstance.GetString(retryTopicKey),
			DLQTopic:                  viperInstance.GetString(dlqTopicKey),
			NotificationsInboundTopic: viperInstance.GetString(notificationsInboundTopicKey),
		},
		Postgres: postgres.Config{
			DSN: viperInstance.GetString(postgresDSNKey),
		},
		Delivery: services.DeliveryConfig{
			Timeout:           time.Duration(viperInstance.GetInt(deliveryTimeoutKey)) * time.Second,
			MaxAttempts:       viperInstance.GetInt(deliveryMaxAttemptsKey),
			RetryBackoff:      time.Duration(viperInstance.GetInt(deliveryRetryBackoffKey)) * time.Second,
			SchedulerInterval: time.Duration(viperInstance.GetInt(deliverySchedulerIntervalKey)) * time.Second,
		},
	}
}

func registerDefaults(viperInstance *viper.Viper) {
	viperInstance.SetDefault(serverHostKey, "0.0.0.0")
	viperInstance.SetDefault(serverPortKey, 8002)

	viperInstance.SetDefault(bootstrapServersKey, "localhost:9092")
	viperInstance.SetDefault(outboxTopicKey, "events.async")
	viperInstance.SetDefault(groupIDKey, "webhook-service.deliveries")
	viperInstance.SetDefault(retryTopicKey, "webhooks.retry")
	viperInstance.SetDefault(dlqTopicKey, "webhooks.dlq")
	viperInstance.SetDefault(notificationsInboundTopicKey, "notifications.inbound")

	viperInstance.SetDefault(postgresDSNKey, "postgres://postgres:postgres@localhost:5432/power_finance_webhooks")

	viperInstance.SetDefault(deliveryTimeoutKey, 10)
	viperInstance.SetDefault(deliveryMaxAttemptsKey, 5)
	viperInstance.SetDefault(deliveryRetryBackoffKey, 30)
	viperInstance.SetDefault(deliverySchedulerIntervalKey, 15)
}

func resolveConfigPath() string {
	if path := os.Getenv(configPathVariable); path != "" {
		return path
	}

	return defaultConfigPath
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
