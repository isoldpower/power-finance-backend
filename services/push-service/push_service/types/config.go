package types

import "time"

type PushServiceConfig struct {
	Server ServerConfig
	Kafka  KafkaConfig
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
