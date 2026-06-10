package http

import (
	"net/http"
	"services/push-service/internal/log"
	"services/push-service/push_service/presentation"
)

type SseHttpConnection struct {
	responseWriter http.ResponseWriter
	request        *http.Request
	controller     *http.ResponseController
}

func NewSseHttpConnection(
	writer http.ResponseWriter,
	request *http.Request,
) presentation.ConnectionPresentation {
	writer.Header().Set("Content-Type", "text/event-stream")
	writer.Header().Set("Cache-Control", "no-cache")
	writer.Header().Set("Connection", "keep-alive")
	writer.Header().Set("Access-Control-Allow-Origin", "*")

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
	_, writeError := hc.responseWriter.Write(message)
	if writeError != nil {
		log.Warnln("Failed to write response %s", message)
		return writeError
	}

	flushError := hc.controller.Flush()
	if flushError != nil {
		log.Warnln("Failed to flush response %s to client at %s", message, hc.request.Host)
		return flushError
	}

	return nil
}
