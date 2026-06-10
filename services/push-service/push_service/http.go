package push_service

import (
	"services/push-service/internal/color"
	"services/push-service/internal/log"
	internalServer "services/push-service/internal/server"
	httpServer "services/push-service/internal/server/http"
	"services/push-service/push_service/handlers"
	httpPresenter "services/push-service/push_service/presentation/http"
)

type pushServiceHttpServerConfig struct {
	httpServer.EstablishedHTTPProcessConfig
}

type pushServiceHttpServer struct {
	sseHandler *handlers.SSENotificationsHandler
	definition *httpPresenter.HttpPresenterDefinition

	*httpServer.HTTPServer
}

func NewPushHTTPServer(config *pushServiceHttpServerConfig) internalServer.Server {
	serverHandler := handlers.NewSSENotificationsHandler()
	serverDefinition := httpPresenter.NewHttpPresenterDefinition(serverHandler)

	basicServer, serverErr := httpServer.NewHTTPServer(config.EstablishedHTTPProcessConfig)
	if serverErr != nil {
		log.PrintError(
			"Failed to create new http server with specified config",
			serverErr,
		)
	}

	return &pushServiceHttpServer{
		sseHandler: handlers.NewSSENotificationsHandler(),
		definition: serverDefinition,
		HTTPServer: basicServer,
	}
}

func (pshs *pushServiceHttpServer) Run(config internalServer.ProcessBootstrapConfig) {
	log.Processln("Running %s HTTP server", log.GetIcon(log.PencilIcon))
	log.RaiseLog(func() {
		log.Logln(
			"%s Press %s to exit",
			log.GetIcon(log.AttentionIcon),
			color.Red("Ctrl+C"),
		)
	})

	pshs.resolveHttpDefinition()
	pshs.HTTPServer.Run(config)
}

func (pshs *pushServiceHttpServer) resolveHttpDefinition() {
	routerErr := pshs.definition.InitialiseRoutes(pshs.HTTPServer)
	if routerErr != nil {
		log.PrintError("Failed to initialise http server", routerErr)
	}
}
