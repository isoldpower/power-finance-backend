package server

import (
	"net/http"
	"time"
)

type HandledRoute struct {
	RoutePattern string
	Handler      http.HandlerFunc
}

type ConnectionInfo struct {
}

type ListenInfo struct {
}

type EnforceShutdownHandler func(message string) error

type ShutdownRoutine struct {
	ForceStop EnforceShutdownHandler
	StartedAt time.Time
}

type Server interface {
	Run(config ProcessBootstrapConfig)
	Shutdown() ShutdownRoutine
	GetDoneChannel() <-chan error
}
