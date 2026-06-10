package server

import (
	"services/push-service/internal/utilities"
)

type ProcessBootstrapConfig struct {
	WithGracefulShutdown bool
	Silent               bool
}

type ProcessConfig struct {
	Host         utilities.Option[string]
	Port         utilities.Option[int]
	ErrorChannel utilities.Option[chan error]
}

type EstablishedProcessConfig struct {
	Host         string
	Port         int
	errorChannel chan error
}

func EstablishProcessConfig(config ProcessConfig) EstablishedProcessConfig {
	config.Port.DefaultOption(8080)
	config.Host.DefaultOption("localhost")
	config.ErrorChannel.DefaultOption(make(chan error, 1))

	return EstablishedProcessConfig{
		Host:         config.Host.Value,
		Port:         config.Port.Value,
		errorChannel: config.ErrorChannel.Value,
	}
}
