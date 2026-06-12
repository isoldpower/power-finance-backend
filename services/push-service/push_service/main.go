package push_service

import (
	"context"

	"services/push-service/internal/health"
	"services/push-service/internal/server"
	httpServer "services/push-service/internal/server/http"
	"services/push-service/internal/utilities"
	"services/push-service/push_service/handlers"
	"services/push-service/push_service/infrastructure/kafka"
	"services/push-service/push_service/services"
	"services/push-service/push_service/types"
)

// StartPushService wires the service and blocks until shutdown; wiring errors fail fast.
func StartPushService(serviceConfig types.PushServiceConfig) error {
	backgroundContext, stopBackgroundServices := context.WithCancel(context.Background())
	defer stopBackgroundServices()

	newHeartbeat := func() types.Heartbeat {
		return services.NewHeartbeatService(serviceConfig.Server.HeartbeatInterval)
	}
	notificationsHandler := handlers.NewSSENotificationsHandler(
		services.NewClientsPoolService(),
		services.NewEventsProjectionService(),
		newHeartbeat,
	)
	notificationsHandler.Start()

	readinessProbe := health.NewProbe()
	kafkaErr := kafka.StartKafkaConsumer(
		backgroundContext,
		serviceConfig.Kafka,
		notificationsHandler.KafkaSink(),
		readinessProbe,
	)
	if kafkaErr != nil {
		return kafkaErr
	}

	establishedConfig := httpServer.EstablishHTTPProcessConfig(httpServer.HTTPProcessConfig{
		ProcessConfig: server.ProcessConfig{
			Host: utilities.BuildOption(serviceConfig.Server.Host),
			Port: utilities.BuildOption(serviceConfig.Server.Port),
		},
	})

	pushHttpServer, serverErr := NewPushHTTPServer(&pushServiceHttpServerConfig{
		EstablishedHTTPProcessConfig: establishedConfig,
	}, notificationsHandler, readinessProbe)
	if serverErr != nil {
		return serverErr
	}

	pushHttpServer.Run(server.ProcessBootstrapConfig{
		WithGracefulShutdown: true,
		Silent:               false,
	})

	return nil
}
