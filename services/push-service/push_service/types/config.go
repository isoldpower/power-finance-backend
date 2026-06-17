package types

import "time"

type PushServiceConfig struct {
	Server  ServerConfig
	Kafka   KafkaConfig
	Logging LoggingConfig
}

type LoggingConfig struct {
	Level string
}

type ServerConfig struct {
	Host              string
	Port              int
	HeartbeatInterval time.Duration
}

type KafkaConfig struct {
	BootstrapServers string
	OutboxTopics     []string
}
