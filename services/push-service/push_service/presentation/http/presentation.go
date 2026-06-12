package http

import (
	"log/slog"
	"net/http"

	"services/push-service/internal/correlation"
	"services/push-service/internal/health"
	"services/push-service/push_service/presentation"
	"services/push-service/push_service/types"
)

type HttpPresentation struct {
	notificationsStream types.NotificationsStream
	readinessProbe      *health.Probe
}

func NewHttpPresentation(
	notificationsStream types.NotificationsStream,
	readinessProbe *health.Probe,
) *HttpPresentation {
	return &HttpPresentation{
		notificationsStream: notificationsStream,
		readinessProbe:      readinessProbe,
	}
}

func (hp *HttpPresentation) HandleHealthCheck(
	writer http.ResponseWriter,
	request *http.Request,
) {
	writer.Header().Set("Content-Type", "text/plain")
	writer.WriteHeader(http.StatusOK)
	_, _ = writer.Write([]byte("ok"))
}

func (hp *HttpPresentation) HandleReadinessCheck(
	writer http.ResponseWriter,
	request *http.Request,
) {
	writer.Header().Set("Content-Type", "text/plain")
	if !hp.readinessProbe.IsReady() {
		writer.WriteHeader(http.StatusServiceUnavailable)
		_, _ = writer.Write([]byte("kafka consumer not running"))
		return
	}

	writer.WriteHeader(http.StatusOK)
	_, _ = writer.Write([]byte("ready"))
}

func (hp *HttpPresentation) HandleGetNotifications(
	writer http.ResponseWriter,
	request *http.Request,
) {
	externalUserID, authenticated := AuthenticatedUserID(request)
	if !authenticated {
		http.Error(writer, "Authenticated user is required", http.StatusUnauthorized)
		return
	}

	requestLogger := correlation.Logger(request.Context()).With("user_id", externalUserID)

	httpConnection := NewSseHttpConnection(writer, request)
	goneChannel := httpConnection.ClientGoneChannel()

	eventsChannel, unsubscribe, subscribed := hp.notificationsStream.Subscribe(externalUserID)
	if subscribed {
		defer unsubscribe()
		requestLogger.Info("sse connection established")
		responseChannel := make(chan []byte)

		go hp.consumeResponseMessages(requestLogger, httpConnection, responseChannel)
		hp.notificationsStream.SpinUntilDone(goneChannel, eventsChannel, responseChannel)

		close(responseChannel)
		requestLogger.Info("sse connection closed")
	}
}

func (hp *HttpPresentation) consumeResponseMessages(
	requestLogger *slog.Logger,
	httpConnection presentation.ConnectionPresentation,
	responseChannel chan []byte,
) {
	for buffer := range responseChannel {
		if transportErr := httpConnection.SendMessageOverConnection(buffer); transportErr != nil {
			requestLogger.Warn("failed to write sse frame", "error", transportErr)
		}
	}
}
