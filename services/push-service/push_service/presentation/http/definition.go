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
		{Pattern: "POST /notifications", Handler: hpd.presentation.HandleGetNotifications},
	}

	for _, route := range routes {
		sourceServer.AddRoute(route.Pattern, route.Handler)
	}

	return nil
}
