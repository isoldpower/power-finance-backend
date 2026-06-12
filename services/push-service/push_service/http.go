package push_service

import (
	"log/slog"

	"services/push-service/internal/health"
	internalServer "services/push-service/internal/server"
	httpServer "services/push-service/internal/server/http"
	httpPresenter "services/push-service/push_service/presentation/http"
	"services/push-service/push_service/types"
)

type pushServiceHttpServerConfig struct {
	httpServer.EstablishedHTTPProcessConfig
}

type pushServiceHttpServer struct {
	definition *httpPresenter.HttpPresenterDefinition

	*httpServer.HTTPServer
}

func NewPushHTTPServer(
	config *pushServiceHttpServerConfig,
	notificationsStream types.NotificationsStream,
	readinessProbe *health.Probe,
) (internalServer.Server, error) {
	serverDefinition := httpPresenter.NewHttpPresenterDefinition(notificationsStream, readinessProbe)

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
