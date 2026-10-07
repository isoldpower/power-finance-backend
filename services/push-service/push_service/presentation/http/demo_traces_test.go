package http

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"services/push-service/internal/health"
	"services/push-service/push_service/types"
)

type unusedDemoTracesStream struct {
	types.NotificationsStream
}

func TestDemoTracesRequiresAValidSessionIdentifier(t *testing.T) {
	presentation := NewHttpPresentation(nil, unusedDemoTracesStream{}, health.NewProbe())

	for _, requestPath := range []string{
		"/api/v1/demo/traces/stream",
		"/api/v1/demo/traces/stream?session=GLOBAL",
		"/api/v1/demo/traces/stream?session=not%20a%20valid%20session%20id",
	} {
		recorder := httptest.NewRecorder()
		presentation.HandleGetDemoTraces(recorder, httptest.NewRequest(http.MethodGet, requestPath, nil))

		if recorder.Code != http.StatusBadRequest {
			t.Fatalf("expected 400 for %q, got %d", requestPath, recorder.Code)
		}
	}
}

func TestDemoTracesIsNotFoundWhenTheStreamIsDisabled(t *testing.T) {
	presentation := NewHttpPresentation(nil, nil, health.NewProbe())
	recorder := httptest.NewRecorder()

	presentation.HandleGetDemoTraces(
		recorder,
		httptest.NewRequest(http.MethodGet, "/api/v1/demo/traces/stream?session=portfolio-visitor-session", nil),
	)

	if recorder.Code != http.StatusNotFound {
		t.Fatalf("expected 404 when the demo stream is disabled, got %d", recorder.Code)
	}
}
