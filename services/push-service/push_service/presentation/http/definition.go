package http

import (
	"services/push-service/internal/health"
	"services/push-service/internal/metrics"
	httpServer "services/push-service/internal/server/http"
	"services/push-service/push_service/types"
)

type HttpPresenterDefinition struct {
	presentation *HttpPresentation
}

func NewHttpPresenterDefinition(
	notificationsStream types.NotificationsStream,
	readinessProbe *health.Probe,
) *HttpPresenterDefinition {
	return &HttpPresenterDefinition{
		presentation: NewHttpPresentation(notificationsStream, readinessProbe),
	}
}

func (hpd *HttpPresenterDefinition) InitialiseRoutes(
	sourceServer *httpServer.HTTPServer,
) error {
	routes := []*httpServer.HttpServerRoute{
		{Pattern: "GET /api/v1/notifications/stream", Handler: hpd.presentation.HandleGetNotifications},
	}
	publicRoutes := []*httpServer.HttpServerRoute{
		{Pattern: "GET /healthz", Handler: hpd.presentation.HandleHealthCheck},
		{Pattern: "GET /readyz", Handler: hpd.presentation.HandleReadinessCheck},
		{Pattern: "GET /metrics", Handler: metrics.Handler().ServeHTTP},
	}

	for _, route := range routes {
		sourceServer.AddRoute(route.Pattern, route.Handler)
	}
	for _, route := range publicRoutes {
		sourceServer.AddPublicRoute(route.Pattern, route.Handler)
	}

	return nil
}

func (hpd *HttpPresenterDefinition) ConfigureMiddlewares(
	sourceServer *httpServer.HTTPServer,
) {
	middlewares := []*httpServer.RouteMiddleware{
		httpServer.NewRouteMiddleware(CorrelationIDMiddleware, correlationMiddlewarePriority),
		httpServer.NewRouteMiddleware(GatewayAuthMiddleware, gatewayAuthMiddlewarePriority),
	}

	for _, middleware := range middlewares {
		sourceServer.RegisterMiddleware(middleware)
	}
}
