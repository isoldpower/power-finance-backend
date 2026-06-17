package http

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
)

type chainStepContextKey struct{}

func appendChainStep(request *http.Request, step string) *http.Request {
	previousSteps, _ := request.Context().Value(chainStepContextKey{}).([]string)
	nextContext := context.WithValue(
		request.Context(),
		chainStepContextKey{},
		append(previousSteps, step),
	)

	return request.WithContext(nextContext)
}

func recordingMiddleware(step string) RouteMiddlewareFunc {
	return func(writer http.ResponseWriter, request *http.Request) (*http.Request, bool) {
		return appendChainStep(request, step), true
	}
}

func rejectingMiddleware(writer http.ResponseWriter, request *http.Request) (*http.Request, bool) {
	writer.WriteHeader(http.StatusUnauthorized)

	return request, false
}

func newServerForMiddlewareTests(t *testing.T) *HTTPServer {
	t.Helper()

	testedServer, serverErr := NewHTTPServer(EstablishHTTPProcessConfig(HTTPProcessConfig{}))
	if serverErr != nil {
		t.Fatal(serverErr)
	}
	t.Cleanup(func() {
		testedServer.listener.Close()
	})

	return testedServer
}

func TestMiddlewaresRunInPriorityOrderAndPassDerivedRequest(t *testing.T) {
	testedServer := newServerForMiddlewareTests(t)
	testedServer.RegisterMiddleware(NewRouteMiddleware(recordingMiddleware("second"), 20))
	testedServer.RegisterMiddleware(NewRouteMiddleware(recordingMiddleware("first"), 10))

	var observedSteps []string
	testedServer.AddRoute("GET /probe", func(writer http.ResponseWriter, request *http.Request) {
		observedSteps, _ = request.Context().Value(chainStepContextKey{}).([]string)
	})

	recorder := httptest.NewRecorder()
	testedServer.router.ServeHTTP(recorder, httptest.NewRequest(http.MethodGet, "/probe", nil))

	if len(observedSteps) != 2 || observedSteps[0] != "first" || observedSteps[1] != "second" {
		t.Fatalf("expected priority-ordered steps [first second], got %v", observedSteps)
	}
}

func TestRejectingMiddlewareStopsChainBeforeHandler(t *testing.T) {
	testedServer := newServerForMiddlewareTests(t)
	testedServer.RegisterMiddleware(NewRouteMiddleware(rejectingMiddleware, 0))

	handlerWasCalled := false
	testedServer.AddRoute("GET /probe", func(writer http.ResponseWriter, request *http.Request) {
		handlerWasCalled = true
	})

	recorder := httptest.NewRecorder()
	testedServer.router.ServeHTTP(recorder, httptest.NewRequest(http.MethodGet, "/probe", nil))

	if handlerWasCalled {
		t.Fatal("expected handler to be skipped after middleware rejection")
	}
	if recorder.Code != http.StatusUnauthorized {
		t.Fatalf("expected middleware status to reach client, got %d", recorder.Code)
	}
}
