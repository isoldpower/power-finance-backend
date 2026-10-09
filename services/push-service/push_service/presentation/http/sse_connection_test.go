package http

import (
	"bufio"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestOpenStreamReachesTheClientBeforeAnyEvent(t *testing.T) {
	streamClosed := make(chan struct{})
	streamServer := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		connection := NewSseHttpConnection(writer, request)
		if openErr := connection.OpenStream(); openErr != nil {
			t.Error(openErr)
			return
		}
		<-streamClosed
	}))
	defer streamServer.Close()
	defer close(streamClosed)

	streamClient := &http.Client{Timeout: 2 * time.Second}
	response, requestErr := streamClient.Get(streamServer.URL)
	if requestErr != nil {
		t.Fatalf("expected headers while the stream stays open, got %v", requestErr)
	}
	defer response.Body.Close()

	if response.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", response.StatusCode)
	}
	if response.Header.Get("Content-Type") != "text/event-stream" {
		t.Fatalf("expected an event stream, got %q", response.Header.Get("Content-Type"))
	}

	openingFrame := make([]byte, len(streamOpenedFrame))
	if _, readErr := io.ReadFull(bufio.NewReader(response.Body), openingFrame); readErr != nil {
		t.Fatalf("expected the opening frame before any event, got %v", readErr)
	}
	if string(openingFrame) != streamOpenedFrame {
		t.Fatalf("expected %q, got %q", streamOpenedFrame, openingFrame)
	}
}
