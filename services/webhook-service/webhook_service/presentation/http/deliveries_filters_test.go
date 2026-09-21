package http

import (
	"errors"
	"net/http"
	"testing"

	"services/webhook-service/webhook_service/services"
)

func TestDeliveryLogPassesFiltersThrough(t *testing.T) {
	log := &fakeDeliveryLog{}
	serve(log, "/api/v1/webhooks/wh-1/deliveries?status=failed&event=transaction.created", "clerk_7")

	query := log.queries[0]
	if query.Filters.Status != "failed" || query.Filters.Event != "transaction.created" {
		t.Fatalf("filters not read: %+v", query.Filters)
	}
	if query.UserExternalID != "clerk_7" || query.WebhookID != "wh-1" {
		t.Fatalf("query not scoped to caller and endpoint: %+v", query)
	}
}

func TestDeliveryLogRefusesAnUnknownStatus(t *testing.T) {
	recorder := serve(&fakeDeliveryLog{}, "/api/v1/webhooks/wh-1/deliveries?status=exploded", "clerk_7")

	if recorder.Code != http.StatusUnprocessableEntity {
		t.Fatalf("expected 422, got %d", recorder.Code)
	}
	failure := decodeBody(t, recorder)["error"].(map[string]any)
	if failure["code"] != "validation_failed" {
		t.Fatalf("unexpected error body: %+v", failure)
	}
}

func TestDeliveryLogRefusesAnUnknownEvent(t *testing.T) {
	recorder := serve(&fakeDeliveryLog{}, "/api/v1/webhooks/wh-1/deliveries?event=transaction.exploded", "clerk_7")

	if recorder.Code != http.StatusUnprocessableEntity {
		t.Fatalf("expected 422, got %d", recorder.Code)
	}
	details := decodeBody(t, recorder)["error"].(map[string]any)["details"].([]any)
	if details[0].(map[string]any)["code"] != "unknown_event_type" {
		t.Fatalf("unexpected detail: %+v", details)
	}
}

func TestDeliveryLogClampsAnOversizedLimit(t *testing.T) {
	log := &fakeDeliveryLog{}
	serve(log, "/api/v1/webhooks/wh-1/deliveries?limit=5000", "clerk_7")

	if log.queries[0].Limit != maximumLimit {
		t.Fatalf("expected the limit clamped to %d, got %d", maximumLimit, log.queries[0].Limit)
	}
}

// Another user's endpoint answers exactly as a missing one does, so the API is
// not an existence oracle.

// Another user's endpoint answers exactly as a missing one does, so the API is
// not an existence oracle.
func TestDeliveryLogHidesEndpointsTheCallerHasNoClaimOn(t *testing.T) {
	log := &fakeDeliveryLog{err: services.ErrWebhookNotFound}
	recorder := serve(log, "/api/v1/webhooks/wh-1/deliveries", "clerk_7")

	if recorder.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", recorder.Code)
	}
}

func TestDeliveryLogSurfacesStoreFailuresAsInternalErrors(t *testing.T) {
	log := &fakeDeliveryLog{err: errors.New("db down")}
	recorder := serve(log, "/api/v1/webhooks/wh-1/deliveries", "clerk_7")

	if recorder.Code != http.StatusInternalServerError {
		t.Fatalf("expected 500, got %d", recorder.Code)
	}
}
