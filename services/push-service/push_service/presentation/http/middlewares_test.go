package http

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"services/push-service/push_service/handlers"
)

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
	request.Header.Set(handlers.GatewayUserHeader, "   ")

	if _, shouldContinue := GatewayAuthMiddleware(recorder, request); shouldContinue {
		t.Fatal("expected blank gateway header to be rejected")
	}
}

func TestGatewayAuthMiddlewarePutsUserIDIntoRequestContext(t *testing.T) {
	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/events", nil)
	request.Header.Set(handlers.GatewayUserHeader, "user_2abc")

	authenticatedRequest, shouldContinue := GatewayAuthMiddleware(recorder, request)

	if !shouldContinue {
		t.Fatal("expected authenticated request to continue")
	}
	userID, present := handlers.AuthenticatedUserID(authenticatedRequest)
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
	if _, present := handlers.AuthenticatedUserID(passedRequest); present {
		t.Fatal("expected preflight request to stay anonymous")
	}
}
