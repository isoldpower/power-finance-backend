package http

import (
	httpServer "services/push-service/internal/server/http"
	"services/push-service/push_service/handlers"
)

type HttpPresenterDefinition struct {
	presentation *HttpPresentation
}

func NewHttpPresenterDefinition(
	handler *handlers.SSENotificationsHandler,
) *HttpPresenterDefinition {
	return &HttpPresenterDefinition{
		presentation: NewHttpPresentation(handler),
	}
}

func (hpd *HttpPresenterDefinition) InitialiseRoutes(
	sourceServer *httpServer.HTTPServer,
) error {
	routes := []*httpServer.HttpServerRoute{
		{Pattern: "GET /events", Handler: hpd.presentation.HandleGetNotifications},
	}

	for _, route := range routes {
		sourceServer.AddRoute(route.Pattern, route.Handler)
	}

	return nil
}

func (hpd *HttpPresenterDefinition) ConfigureMiddlewares(
	sourceServer *httpServer.HTTPServer,
) {
	middlewares := []*httpServer.RouteMiddleware{
		httpServer.NewRouteMiddleware(GatewayAuthMiddleware, gatewayAuthMiddlewarePriority),
	}

	for _, middleware := range middlewares {
		sourceServer.RegisterMiddleware(middleware)
	}
}
