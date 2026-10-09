package http

import (
	"log/slog"
	"net/http"

	"services/push-service/internal/correlation"
	"services/push-service/internal/health"
	"services/push-service/push_service/presentation"
	"services/push-service/push_service/types"
)

const (
	demoSessionQueryParameter          = "session"
	infrastructureTopologyCacheControl = "public, max-age=300"
)

type HttpPresentation struct {
	notificationsStream types.NotificationsStream
	demoSurface         types.DemoSurface
	readinessProbe      *health.Probe
}

func NewHttpPresentation(
	notificationsStream types.NotificationsStream,
	demoSurface types.DemoSurface,
	readinessProbe *health.Probe,
) *HttpPresentation {
	return &HttpPresentation{
		notificationsStream: notificationsStream,
		demoSurface:         demoSurface,
		readinessProbe:      readinessProbe,
	}
}

// HandleHealthCheck checks whether connection is healthy.
func (hp *HttpPresentation) HandleHealthCheck(
	writer http.ResponseWriter,
	request *http.Request,
) {
	writer.Header().Set("Content-Type", "text/plain")
	writer.WriteHeader(http.StatusOK)
	_, _ = writer.Write([]byte("ok"))
}

// HandleReadinessCheck checks whether connection is ready
// to send/receive new data.
func (hp *HttpPresentation) HandleReadinessCheck(
	writer http.ResponseWriter,
	request *http.Request,
) {
	writer.Header().Set("Content-Type", "text/plain")
	if !hp.readinessProbe.IsReady() {
		writer.WriteHeader(http.StatusServiceUnavailable)
		_, writeErr := writer.Write([]byte("kafka consumer not running"))
		if writeErr != nil {
			slog.Warn("readiness response write failed", "error", writeErr)
		}

		return
	}

	writer.WriteHeader(http.StatusOK)
	_, writeErr := writer.Write([]byte("ready"))
	if writeErr != nil {
		slog.Warn("readiness response write failed", "error", writeErr)
	}
}

// HandleGetNotifications is a presentation method for subscribing a connection
// to receiving events via SSE long-lived connection.
func (hp *HttpPresentation) HandleGetNotifications(
	writer http.ResponseWriter,
	request *http.Request,
) {
	externalUserID, isAuthenticated := AuthenticatedUserID(request)
	if !isAuthenticated {
		http.Error(writer, "Authenticated user is required", http.StatusUnauthorized)
		return
	}

	requestLogger := correlation.
		Logger(request.Context()).
		With("user_id", externalUserID)
	httpConnection := NewSseHttpConnection(writer, request)
	goneChannel := httpConnection.ClientGoneChannel()

	eventsChannel, unsubscribe, isSubscribed := hp.notificationsStream.Subscribe(externalUserID)
	if isSubscribed {
		defer unsubscribe()
		hp.runEventsStream(
			hp.notificationsStream,
			requestLogger,
			httpConnection,
			eventsChannel,
			goneChannel,
		)
	}
}

func (hp *HttpPresentation) HandleGetDemoTraces(
	writer http.ResponseWriter,
	request *http.Request,
) {
	if hp.demoSurface.TracesStream == nil || hp.demoSurface.IsValidDemoSessionIdentifier == nil {
		http.Error(writer, "Demo traces stream is disabled", http.StatusNotFound)
		return
	}

	demoSessionIdentifier := request.URL.Query().Get(demoSessionQueryParameter)
	if !hp.demoSurface.IsValidDemoSessionIdentifier(demoSessionIdentifier) {
		http.Error(writer, "A valid demo session identifier is required", http.StatusBadRequest)
		return
	}

	requestLogger := correlation.
		Logger(request.Context()).
		With("demo_session", demoSessionIdentifier)

	httpConnection := NewSseHttpConnection(writer, request)
	goneChannel := httpConnection.ClientGoneChannel()
	spansChannel, unsubscribe, isSubscribed := hp.demoSurface.TracesStream.Subscribe(demoSessionIdentifier)
	if isSubscribed {
		defer unsubscribe()
		hp.runEventsStream(
			hp.demoSurface.TracesStream,
			requestLogger,
			httpConnection,
			spansChannel,
			goneChannel,
		)
	}
}

func (hp *HttpPresentation) HandleGetInfrastructureTopology(
	writer http.ResponseWriter,
	request *http.Request,
) {
	if len(hp.demoSurface.InfrastructureTopologyDocument) == 0 {
		http.Error(writer, "Infrastructure topology is unavailable", http.StatusNotFound)
		return
	}

	writer.Header().Set("Content-Type", "application/json")
	writer.Header().Set("Cache-Control", infrastructureTopologyCacheControl)
	writer.WriteHeader(http.StatusOK)
	if _, writeErr := writer.Write(hp.demoSurface.InfrastructureTopologyDocument); writeErr != nil {
		slog.Warn("infrastructure topology response write failed", "error", writeErr)
	}
}

func (hp *HttpPresentation) runEventsStream(
	eventsStream types.NotificationsStream,
	requestLogger *slog.Logger,
	connection presentation.ConnectionPresentation,
	eventsChannel <-chan types.OutboxEvent,
	goneChannel <-chan struct{},
) {
	if openErr := connection.OpenStream(); openErr != nil {
		requestLogger.Warn("failed to open sse stream", "error", openErr)
		return
	}

	requestLogger.Info("sse connection established")
	responseChannel := make(chan []byte)

	go hp.consumeResponseMessages(requestLogger, connection, responseChannel)
	eventsStream.SpinUntilDone(goneChannel, eventsChannel, responseChannel)

	close(responseChannel)
	requestLogger.Info("sse connection closed")
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
