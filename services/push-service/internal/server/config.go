package server

import (
	"services/push-service/internal/utilities"
)

type ProcessBootstrapConfig struct {
	WithGracefulShutdown bool
	Silent               bool
}

type ProcessConfig struct {
	Host utilities.Option[string]
	Port utilities.Option[int]
}

type EstablishedProcessConfig struct {
	Host string
	Port int
}

func EstablishProcessConfig(config ProcessConfig) EstablishedProcessConfig {
	config.Port.DefaultOption(8080)
	config.Host.DefaultOption("localhost")

	return EstablishedProcessConfig{
		Host: config.Host.Value,
		Port: config.Port.Value,
	}
}
