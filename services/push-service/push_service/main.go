package push_service

import (
	"services/push-service/internal/server"
	httpServer "services/push-service/internal/server/http"
	"services/push-service/internal/utilities"
)

func StartPushService() {
	serverErrorChannel := make(chan error, 1)
	establishedConfig := httpServer.EstablishHTTPProcessConfig(httpServer.HTTPProcessConfig{
		ProcessConfig: server.ProcessConfig{
			Host:         utilities.BuildOption("localhost"),
			Port:         utilities.BuildOption(8001),
			ErrorChannel: utilities.BuildOption(serverErrorChannel),
		},
	})

	pushHttpServer := NewPushHTTPServer(&pushServiceHttpServerConfig{
		EstablishedHTTPProcessConfig: establishedConfig,
	})
	pushHttpServer.Run(server.ProcessBootstrapConfig{
		WithGracefulShutdown: true,
		Silent:               false,
	})
}
