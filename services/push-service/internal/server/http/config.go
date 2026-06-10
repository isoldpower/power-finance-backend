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

	server.ProcessConfig
}

type EstablishedHTTPProcessConfig struct {
	NetworkType HTTPNetworkType

	server.EstablishedProcessConfig
}

func EstablishHTTPProcessConfig(config HTTPProcessConfig) EstablishedHTTPProcessConfig {
	config.NetworkType.DefaultOption(NetworkTypeTCP)

	return EstablishedHTTPProcessConfig{
		EstablishedProcessConfig: server.EstablishProcessConfig(config.ProcessConfig),
		NetworkType:              config.NetworkType.Value,
	}
}
