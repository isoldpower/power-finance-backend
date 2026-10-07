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

func acceptOnlyPortfolioVisitorSession(candidateIdentifier string) bool {
	return candidateIdentifier == "portfolio-visitor-session"
}

func TestDemoTracesRequiresAValidSessionIdentifier(t *testing.T) {
	presentation := NewHttpPresentation(nil, types.DemoSurface{
		TracesStream:                 unusedDemoTracesStream{},
		IsValidDemoSessionIdentifier: acceptOnlyPortfolioVisitorSession,
	}, health.NewProbe())

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
	presentation := NewHttpPresentation(nil, types.DemoSurface{
		IsValidDemoSessionIdentifier: acceptOnlyPortfolioVisitorSession,
	}, health.NewProbe())
	recorder := httptest.NewRecorder()

	presentation.HandleGetDemoTraces(
		recorder,
		httptest.NewRequest(http.MethodGet, "/api/v1/demo/traces/stream?session=portfolio-visitor-session", nil),
	)

	if recorder.Code != http.StatusNotFound {
		t.Fatalf("expected 404 when the demo stream is disabled, got %d", recorder.Code)
	}
}

func TestInfrastructureTopologyIsServedAsCacheableJSON(t *testing.T) {
	presentation := NewHttpPresentation(nil, types.DemoSurface{
		InfrastructureTopologyDocument: []byte(`{"version":1}`),
	}, health.NewProbe())
	recorder := httptest.NewRecorder()

	presentation.HandleGetInfrastructureTopology(
		recorder,
		httptest.NewRequest(http.MethodGet, "/api/v1/demo/topology", nil),
	)

	if recorder.Code != http.StatusOK || recorder.Body.String() != `{"version":1}` {
		t.Fatalf("expected the topology document, got %d %q", recorder.Code, recorder.Body.String())
	}
	if recorder.Header().Get("Content-Type") != "application/json" {
		t.Fatalf("expected a JSON content type, got %q", recorder.Header().Get("Content-Type"))
	}
	if recorder.Header().Get("Cache-Control") != infrastructureTopologyCacheControl {
		t.Fatalf("expected the topology to be cacheable, got %q", recorder.Header().Get("Cache-Control"))
	}
}

func TestInfrastructureTopologyIsNotFoundWithoutADocument(t *testing.T) {
	presentation := NewHttpPresentation(nil, types.DemoSurface{}, health.NewProbe())
	recorder := httptest.NewRecorder()

	presentation.HandleGetInfrastructureTopology(
		recorder,
		httptest.NewRequest(http.MethodGet, "/api/v1/demo/topology", nil),
	)

	if recorder.Code != http.StatusNotFound {
		t.Fatalf("expected 404 without a topology document, got %d", recorder.Code)
	}
}
