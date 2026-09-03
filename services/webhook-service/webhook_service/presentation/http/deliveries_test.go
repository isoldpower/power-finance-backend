package http

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"services/webhook-service/webhook_service/presentation/http/contract"
	"testing"
	"time"

	"services/webhook-service/internal/health"
	"services/webhook-service/webhook_service/services"
	"services/webhook-service/webhook_service/types"
)

type fakeDeliveryLog struct {
	page    types.DeliveryLogPage
	err     error
	queries []types.DeliveryLogQuery
}

func (f *fakeDeliveryLog) List(_ context.Context, query types.DeliveryLogQuery) (types.DeliveryLogPage, error) {
	f.queries = append(f.queries, query)

	return f.page, f.err
}

func deliveryRows(count int) []types.Delivery {
	base := time.Date(2026, 8, 12, 11, 51, 0, 0, time.UTC)
	rows := make([]types.Delivery, 0, count)
	for index := 0; index < count; index++ {
		rows = append(rows, types.Delivery{
			ID:        string(rune('a' + index)),
			WebhookID: "wh-1",
			EventID:   "evt-1",
			EventType: "transaction.created",
			TargetURL: "https://hooks.example.com/x",
			Status:    types.DeliverySuccess,
			Attempts:  1,
			CreatedAt: base.Add(-time.Duration(index) * time.Minute),
			UpdatedAt: base.Add(-time.Duration(index) * time.Minute),
		})
	}

	return rows
}

func serve(log deliveryLogReader, target string, userID string) *httptest.ResponseRecorder {
	server := NewServer(contract.Config{}, health.NewProbe(), log)
	request := httptest.NewRequest(http.MethodGet, target, nil)
	if userID != "" {
		request.Header.Set(GatewayUserHeader, userID)
	}
	recorder := httptest.NewRecorder()
	server.server.Handler.ServeHTTP(recorder, request)

	return recorder
}

func decodeBody(t *testing.T, recorder *httptest.ResponseRecorder) map[string]any {
	t.Helper()

	var body map[string]any
	if err := json.Unmarshal(recorder.Body.Bytes(), &body); err != nil {
		t.Fatalf("response is not JSON: %v (%s)", err, recorder.Body.String())
	}

	return body
}

func TestDeliveryLogRequiresTheGatewayHeader(t *testing.T) {
	recorder := serve(&fakeDeliveryLog{}, "/api/v1/webhooks/wh-1/deliveries", "")

	if recorder.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401, got %d", recorder.Code)
	}
}

func TestDeliveryLogServesTheEnvelope(t *testing.T) {
	log := &fakeDeliveryLog{page: types.DeliveryLogPage{Rows: deliveryRows(2), Total: 2}}
	recorder := serve(log, "/api/v1/webhooks/wh-1/deliveries", "clerk_7")

	if recorder.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d (%s)", recorder.Code, recorder.Body.String())
	}

	body := decodeBody(t, recorder)
	meta := body["meta"].(map[string]any)
	if meta["total"].(float64) != 2 || meta["limit"].(float64) != defaultLimit {
		t.Fatalf("unexpected meta: %+v", meta)
	}
	if meta["next_cursor"] != nil || meta["prev_cursor"] != nil {
		t.Fatalf("a single complete page has nothing to navigate to: %+v", meta)
	}

	rows := body["data"].([]any)
	first := rows[0].(map[string]any)
	if first["event"] != "transaction.created" || first["event_id"] != "evt-1" {
		t.Fatalf("unexpected row: %+v", first)
	}
}

// Echoing the payload would double the size of every page and can restate
// money the read model has since superseded.
func TestDeliveryLogNeverReturnsThePayload(t *testing.T) {
	rows := deliveryRows(1)
	rows[0].Payload = []byte(`{"secret":"do-not-echo"}`)
	log := &fakeDeliveryLog{page: types.DeliveryLogPage{Rows: rows, Total: 1}}

	recorder := serve(log, "/api/v1/webhooks/wh-1/deliveries", "clerk_7")

	row := decodeBody(t, recorder)["data"].([]any)[0].(map[string]any)
	if _, present := row["payload"]; present {
		t.Fatalf("payload must not be returned: %+v", row)
	}
}

// A finished delivery has nothing scheduled and no error to show.
func TestFinishedDeliveryReportsNullsRatherThanBlanks(t *testing.T) {
	log := &fakeDeliveryLog{page: types.DeliveryLogPage{Rows: deliveryRows(1), Total: 1}}
	recorder := serve(log, "/api/v1/webhooks/wh-1/deliveries", "clerk_7")

	row := decodeBody(t, recorder)["data"].([]any)[0].(map[string]any)
	if row["next_attempt_at"] != nil || row["last_error"] != nil {
		t.Fatalf("expected nulls on a finished delivery: %+v", row)
	}
}

func TestDeliveryLogMintsANextCursorWhenMoreRowsExist(t *testing.T) {
	log := &fakeDeliveryLog{page: types.DeliveryLogPage{Rows: deliveryRows(3), Total: 3}}
	recorder := serve(log, "/api/v1/webhooks/wh-1/deliveries?limit=2", "clerk_7")

	body := decodeBody(t, recorder)
	if len(body["data"].([]any)) != 2 {
		t.Fatalf("lookahead row should not be served: %+v", body["data"])
	}
	if body["meta"].(map[string]any)["next_cursor"] == nil {
		t.Fatal("expected a next cursor when a further page exists")
	}
}

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
