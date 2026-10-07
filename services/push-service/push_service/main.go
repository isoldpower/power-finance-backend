package push_service

import (
	"context"

	"github.com/power-finance/observability-go/tracing"

	"services/push-service/push_service/presentation/http"

	"services/push-service/internal/health"
	"services/push-service/internal/server"
	httpServer "services/push-service/internal/server/http"
	"services/push-service/internal/utilities"
	"services/push-service/push_service/handlers"
	"services/push-service/push_service/infrastructure/kafka"
	"services/push-service/push_service/services"
	"services/push-service/push_service/types"
)

const defaultTracingServiceName = "push-service"

// StartPushService wires the service and blocks until shutdown; wiring errors fail fast.
func StartPushService(serviceConfig types.PushServiceConfig) error {
	backgroundContext, stopBackgroundServices := context.WithCancel(context.Background())
	defer stopBackgroundServices()

	_, shutdownTracing, tracingErr := tracing.Configure(backgroundContext, defaultTracingServiceName)
	if tracingErr != nil {
		return tracingErr
	}
	defer func() {
		shutdownContext, cancelShutdown := context.WithTimeout(
			context.Background(),
			tracing.ShutdownTimeout(),
		)
		defer cancelShutdown()
		_ = shutdownTracing(shutdownContext)
	}()

	newHeartbeat := func() types.Heartbeat {
		return services.NewHeartbeatService(serviceConfig.Server.HeartbeatInterval)
	}
	notificationsHandler := handlers.NewSSEStreamHandler(
		services.NewClientsPoolService(),
		services.NewEventsProjectionService(),
		newHeartbeat,
	)
	notificationsHandler.Start(backgroundContext)

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

	demoTracesStream, demoTracesErr := startDemoTracesStream(
		backgroundContext,
		serviceConfig,
		newHeartbeat,
	)
	if demoTracesErr != nil {
		return demoTracesErr
	}

	establishedConfig := httpServer.EstablishHTTPProcessConfig(httpServer.HTTPProcessConfig{
		ProcessConfig: server.ProcessConfig{
			Host: utilities.BuildOption(serviceConfig.Server.Host),
			Port: utilities.BuildOption(serviceConfig.Server.Port),
		},
	})

	pushHttpServer, serverErr := http.NewPushHTTPServer(
		http.NewPushHTTPConfig(establishedConfig),
		notificationsHandler,
		demoTracesStream,
		readinessProbe,
	)

	if serverErr == nil {
		pushHttpServer.Run(server.ProcessBootstrapConfig{
			WithGracefulShutdown: true,
			Silent:               false,
		})
	}

	return serverErr
}

func startDemoTracesStream(
	backgroundContext context.Context,
	serviceConfig types.PushServiceConfig,
	newHeartbeat types.HeartbeatFactory,
) (types.DemoTracesStream, error) {
	if serviceConfig.Kafka.DemoSpansTopic == "" {
		return nil, nil
	}

	demoTracesHandler := handlers.NewSSEStreamHandler(
		services.NewClientsPoolService(),
		services.NewDemoSpansProjectionService(),
		newHeartbeat,
	)
	demoTracesHandler.Start(backgroundContext)

	demoSpansConsumerErr := kafka.StartDemoSpansConsumer(
		backgroundContext,
		serviceConfig.Kafka,
		demoTracesHandler.KafkaSink(),
		health.NewProbe(),
	)
	if demoSpansConsumerErr != nil {
		return nil, demoSpansConsumerErr
	}

	return demoTracesHandler, nil
}
