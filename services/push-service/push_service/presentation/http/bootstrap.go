package http

import (
	"log/slog"

	"services/push-service/internal/health"
	internalServer "services/push-service/internal/server"
	httpServer "services/push-service/internal/server/http"
	"services/push-service/push_service/types"
)

type pushServiceHttpServerConfig struct {
	httpServer.EstablishedHTTPProcessConfig
}

func NewPushHTTPConfig(config httpServer.EstablishedHTTPProcessConfig) *pushServiceHttpServerConfig {
	return &pushServiceHttpServerConfig{
		EstablishedHTTPProcessConfig: config,
	}
}

type pushServiceHttpServer struct {
	definition *HttpPresenterDefinition

	*httpServer.HTTPServer
}

func NewPushHTTPServer(
	config *pushServiceHttpServerConfig,
	notificationsStream types.NotificationsStream,
	readinessProbe *health.Probe,
) (internalServer.Server, error) {
	serverDefinition := NewHttpPresenterDefinition(notificationsStream, readinessProbe)

	basicServer, serverErr := httpServer.NewHTTPServer(config.EstablishedHTTPProcessConfig)
	if serverErr != nil {
		return nil, serverErr
	}

	return &pushServiceHttpServer{
		definition: serverDefinition,
		HTTPServer: basicServer,
	}, nil
}

func (pshs *pushServiceHttpServer) Run(config internalServer.ProcessBootstrapConfig) {
	slog.Info("http server starting")

	pshs.resolveHttpDefinition()
	pshs.HTTPServer.Run(config)
}

func (pshs *pushServiceHttpServer) resolveHttpDefinition() {
	pshs.definition.ConfigureMiddlewares(pshs.HTTPServer)

	routerErr := pshs.definition.InitialiseRoutes(pshs.HTTPServer)
	if routerErr != nil {
		slog.Error("failed to initialise http routes", "error", routerErr)
	}
}
