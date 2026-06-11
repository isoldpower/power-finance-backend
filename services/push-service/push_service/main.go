package push_service

import (
	"context"
	"os"
	"strconv"

	"services/push-service/internal/log"
	"services/push-service/internal/server"
	httpServer "services/push-service/internal/server/http"
	"services/push-service/internal/utilities"
	"services/push-service/push_service/handlers"
	"services/push-service/push_service/infrastructure/kafka"
)

const (
	defaultServerHost = "localhost"
	defaultServerPort = 8001
)

func StartPushService() {
	backgroundContext, stopBackgroundServices := context.WithCancel(context.Background())
	defer stopBackgroundServices()

	notificationsHandler := handlers.NewSSENotificationsHandler()
	kafka.StartKafkaConsumer(backgroundContext, notificationsHandler.KafkaSink())

	serverErrorChannel := make(chan error, 1)
	establishedConfig := httpServer.EstablishHTTPProcessConfig(httpServer.HTTPProcessConfig{
		ProcessConfig: server.ProcessConfig{
			Host:         utilities.BuildOption(serverHostFromEnv()),
			Port:         utilities.BuildOption(serverPortFromEnv()),
			ErrorChannel: utilities.BuildOption(serverErrorChannel),
		},
	})

	pushHttpServer := NewPushHTTPServer(&pushServiceHttpServerConfig{
		EstablishedHTTPProcessConfig: establishedConfig,
	}, notificationsHandler)
	pushHttpServer.Run(server.ProcessBootstrapConfig{
		WithGracefulShutdown: true,
		Silent:               false,
	})
}

func serverHostFromEnv() string {
	if host := os.Getenv("PUSH_SERVICE_HOST"); host != "" {
		return host
	}

	return defaultServerHost
}

func serverPortFromEnv() int {
	rawPort := os.Getenv("PUSH_SERVICE_PORT")
	if rawPort == "" {
		return defaultServerPort
	}

	port, parseErr := strconv.Atoi(rawPort)
	if parseErr != nil {
		log.Warnln("Invalid PUSH_SERVICE_PORT %q; using default %d", rawPort, defaultServerPort)
		return defaultServerPort
	}

	return port
}
