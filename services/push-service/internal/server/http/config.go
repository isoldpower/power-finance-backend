package http

import (
	"services/push-service/internal/server"
	"services/push-service/internal/utilities"
)

type HTTPNetworkType string

const (
	NetworkTypeTCP         HTTPNetworkType = "tcp"
	NetworkTypeTCP4        HTTPNetworkType = "tcp4"
	NetworkTypeTCP6        HTTPNetworkType = "tcp6"
	NetworkTypeUnix        HTTPNetworkType = "unix"
	NetworkTypeUnixNetwork HTTPNetworkType = "unixpacket"
)

type HTTPProcessConfig struct {
	NetworkType utilities.Option[HTTPNetworkType]
	Middlewares utilities.Option[[]*RouteMiddleware]

	server.ProcessConfig
}

type EstablishedHTTPProcessConfig struct {
	NetworkType HTTPNetworkType
	Middlewares []*RouteMiddleware

	server.EstablishedProcessConfig
}

// EstablishHTTPProcessConfig serves as a way to populate default values to
// server config so the process can run safely without failing due to missed variable.
func EstablishHTTPProcessConfig(config HTTPProcessConfig) EstablishedHTTPProcessConfig {
	config.NetworkType.DefaultOption(NetworkTypeTCP)
	config.Middlewares.DefaultOption(make([]*RouteMiddleware, 0))

	return EstablishedHTTPProcessConfig{
		EstablishedProcessConfig: server.EstablishProcessConfig(config.ProcessConfig),
		Middlewares:              sortMiddlewares(config.Middlewares.Value),
		NetworkType:              config.NetworkType.Value,
	}
}
