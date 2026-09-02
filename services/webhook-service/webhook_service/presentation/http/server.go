package http

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"time"

	"services/webhook-service/internal/health"
	"services/webhook-service/internal/metrics"
)

type Server struct {
	server         *http.Server
	readinessProbe *health.Probe
	deliveryLog    deliveryLogReader
}

func NewServer(
	serverConfig Config,
	readinessProbe *health.Probe,
	deliveryLog deliveryLogReader,
) *Server {
	router := http.NewServeMux()
	httpServer := &Server{
		server: &http.Server{
			Addr:              fmt.Sprintf("%s:%d", serverConfig.Host, serverConfig.Port),
			Handler:           router,
			ReadHeaderTimeout: 5 * time.Second,
		},
		readinessProbe: readinessProbe,
		deliveryLog:    deliveryLog,
	}

	router.HandleFunc("GET /healthz", httpServer.handleHealthCheck)
	router.HandleFunc("GET /readyz", httpServer.handleReadinessCheck)
	router.Handle("GET /metrics", metrics.Handler())
	router.HandleFunc(
		"GET /api/v1/webhooks/{webhookID}/deliveries",
		httpServer.handleDeliveryLog,
	)

	return httpServer
}

// Run serves until the context is cancelled, then shuts down gracefully.
func (s *Server) Run(ctx context.Context) {
	go func() {
		slog.Info("http server listening", "addr", s.server.Addr)
		if serveErr := s.server.ListenAndServe(); serveErr != nil && !errors.Is(serveErr, http.ErrServerClosed) {
			slog.Error("http listener serve failed", "error", serveErr)
		}
	}()

	<-ctx.Done()
	shutdownContext, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if shutdownErr := s.server.Shutdown(shutdownContext); shutdownErr != nil {
		slog.Error("http server shutdown failed", "error", shutdownErr)
	}
}

func (s *Server) handleHealthCheck(writer http.ResponseWriter, _ *http.Request) {
	writer.WriteHeader(http.StatusOK)
	_, _ = writer.Write([]byte(`{"status":"ok"}`))
}

func (s *Server) handleReadinessCheck(writer http.ResponseWriter, _ *http.Request) {
	if !s.readinessProbe.IsReady() {
		writer.WriteHeader(http.StatusServiceUnavailable)
		_, _ = writer.Write([]byte(`{"status":"unready"}`))
		return
	}

	writer.WriteHeader(http.StatusOK)
	_, _ = writer.Write([]byte(`{"status":"ready"}`))
}
