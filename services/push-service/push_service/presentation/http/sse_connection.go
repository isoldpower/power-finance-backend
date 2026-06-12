package http

import (
	"net/http"

	"services/push-service/push_service/presentation"
)

type SseHttpConnection struct {
	responseWriter http.ResponseWriter
	request        *http.Request
	controller     *http.ResponseController
}

// CORS headers are deliberately absent — the API gateway owns CORS policy.
func NewSseHttpConnection(
	writer http.ResponseWriter,
	request *http.Request,
) presentation.ConnectionPresentation {
	writer.Header().Set("Content-Type", "text/event-stream")
	writer.Header().Set("Cache-Control", "no-cache")
	writer.Header().Set("Connection", "keep-alive")

	responseController := http.NewResponseController(writer)

	return &SseHttpConnection{
		request:        request,
		responseWriter: writer,
		controller:     responseController,
	}
}

func (hc *SseHttpConnection) ClientGoneChannel() <-chan struct{} {
	return hc.request.Context().Done()
}

func (hc *SseHttpConnection) SendMessageOverConnection(message []byte) error {
	if _, writeError := hc.responseWriter.Write(message); writeError != nil {
		return writeError
	}

	return hc.controller.Flush()
}
