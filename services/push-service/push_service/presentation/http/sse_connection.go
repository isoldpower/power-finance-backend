package http

import (
	"net/http"
	"time"

	"services/push-service/push_service/presentation"
)

// writeTimeout bounds a single SSE frame write so a half-open client connection
// cannot block the writer goroutine indefinitely.
const writeTimeout = 10 * time.Second

type SseHttpConnection struct {
	responseWriter http.ResponseWriter
	request        *http.Request
	controller     *http.ResponseController
}

// NewSseHttpConnection CORS headers are deliberately absent.
// The API gateway owns CORS policy.
func NewSseHttpConnection(
	writer http.ResponseWriter,
	request *http.Request,
) presentation.ConnectionPresentation {
	writer.Header().Set("Content-Type", "text/event-stream")
	writer.Header().Set("Cache-Control", "no-cache")
	writer.Header().Set("Connection", "keep-alive")
	writer.Header().Set("X-Accel-Buffering", "no")

	responseController := http.NewResponseController(writer)

	return &SseHttpConnection{
		request:        request,
		responseWriter: writer,
		controller:     responseController,
	}
}

// ClientGoneChannel returns connection's channel representing disconnection signal.
func (hc *SseHttpConnection) ClientGoneChannel() <-chan struct{} {
	return hc.request.Context().Done()
}

// SendMessageOverConnection is a helper method to send the payload over an established connection.
func (hc *SseHttpConnection) SendMessageOverConnection(message []byte) error {
	if deadlineErr := hc.controller.SetWriteDeadline(time.Now().Add(writeTimeout)); deadlineErr != nil {
		return deadlineErr
	}

	if _, writeError := hc.responseWriter.Write(message); writeError != nil {
		return writeError
	}

	return hc.controller.Flush()
}
