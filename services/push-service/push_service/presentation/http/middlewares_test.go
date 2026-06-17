package http

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"services/push-service/internal/correlation"
)

func TestCorrelationIDMiddlewarePropagatesGatewayHeader(t *testing.T) {
	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/events", nil)
	request.Header.Set(correlation.Header, "corr-123")

	correlatedRequest, shouldContinue := CorrelationIDMiddleware(recorder, request)

	if !shouldContinue {
		t.Fatal("expected request to continue")
	}
	correlationID, present := correlation.ID(correlatedRequest.Context())
	if !present || correlationID != "corr-123" {
		t.Fatalf("expected corr-123 in context, got %q/%v", correlationID, present)
	}
	if recorder.Header().Get(correlation.Header) != "corr-123" {
		t.Fatal("expected correlation id to be echoed on the response")
	}
}

func TestCorrelationIDMiddlewareGeneratesFallbackID(t *testing.T) {
	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/events", nil)

	correlatedRequest, _ := CorrelationIDMiddleware(recorder, request)

	correlationID, present := correlation.ID(correlatedRequest.Context())
	if !present || correlationID == "" {
		t.Fatal("expected a generated correlation id")
	}
	if recorder.Header().Get(correlation.Header) != correlationID {
		t.Fatal("expected generated id to be echoed on the response")
	}
}

func TestGatewayAuthMiddlewareRejectsWithoutUserHeader(t *testing.T) {
	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/events", nil)

	_, shouldContinue := GatewayAuthMiddleware(recorder, request)

	if shouldContinue {
		t.Fatal("expected request without gateway header to be rejected")
	}
	if recorder.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401, got %d", recorder.Code)
	}
}

func TestGatewayAuthMiddlewareRejectsBlankUserHeader(t *testing.T) {
	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/events", nil)
	request.Header.Set(GatewayUserHeader, "   ")

	if _, shouldContinue := GatewayAuthMiddleware(recorder, request); shouldContinue {
		t.Fatal("expected blank gateway header to be rejected")
	}
}

func TestGatewayAuthMiddlewarePutsUserIDIntoRequestContext(t *testing.T) {
	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/events", nil)
	request.Header.Set(GatewayUserHeader, "user_2abc")

	authenticatedRequest, shouldContinue := GatewayAuthMiddleware(recorder, request)

	if !shouldContinue {
		t.Fatal("expected authenticated request to continue")
	}
	userID, present := AuthenticatedUserID(authenticatedRequest)
	if !present || userID != "user_2abc" {
		t.Fatalf("expected user_2abc in context, got %q/%v", userID, present)
	}
}

func TestGatewayAuthMiddlewareSkipsPreflightRequests(t *testing.T) {
	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodOptions, "/events", nil)

	passedRequest, shouldContinue := GatewayAuthMiddleware(recorder, request)

	if !shouldContinue {
		t.Fatal("expected preflight request to pass without authentication")
	}
	if _, present := AuthenticatedUserID(passedRequest); present {
		t.Fatal("expected preflight request to stay anonymous")
	}
}
