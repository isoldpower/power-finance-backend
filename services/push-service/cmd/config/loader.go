package config

import (
	"log/slog"
	"os"
	"strings"
	"time"

	"github.com/spf13/viper"

	"services/push-service/push_service/types"
)

const (
	configPathVariable = "PUSH_SERVICE_CONFIG_FILE"
	defaultConfigPath  = "./config.yaml"

	serverHostKey        = "push_service.host"
	serverPortKey        = "push_service.port"
	heartbeatIntervalKey = "push_service.heartbeat_interval_seconds"

	bootstrapServersKey = "kafka.bootstrap_servers"
	outboxTopicKey      = "kafka.outbox_topic"

	logLevelKey = "log_level"
)

// Load resolves and composes all the Viper-based project configurations.
func Load() types.PushServiceConfig {
	viperInstance := viper.New()
	registerDefaults(viperInstance)

	configPath := resolveConfigPath()
	ResolveViper(viperInstance, configPath)
	if resolveErr := TryResolveConfig(viperInstance); resolveErr != nil {
		slog.Warn("failed to read config file", "path", configPath, "error", resolveErr)
	}

	return types.PushServiceConfig{
		Server: types.ServerConfig{
			Host:              viperInstance.GetString(serverHostKey),
			Port:              viperInstance.GetInt(serverPortKey),
			HeartbeatInterval: time.Duration(viperInstance.GetInt(heartbeatIntervalKey)) * time.Second,
		},
		Kafka: types.KafkaConfig{
			BootstrapServers: viperInstance.GetString(bootstrapServersKey),
			OutboxTopics:     splitTopics(viperInstance.GetString(outboxTopicKey)),
		},
		Logging: types.LoggingConfig{
			Level: viperInstance.GetString(logLevelKey),
		},
	}
}

func registerDefaults(viperInstance *viper.Viper) {
	viperInstance.SetDefault(serverHostKey, "localhost")
	viperInstance.SetDefault(serverPortKey, 8001)
	viperInstance.SetDefault(heartbeatIntervalKey, 15)

	viperInstance.SetDefault(bootstrapServersKey, "localhost:9092")
	viperInstance.SetDefault(outboxTopicKey, "events.async")

	viperInstance.SetDefault(logLevelKey, "info")
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
