package metrics

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestHandlerExposesPushMetrics(t *testing.T) {
	KafkaEventReceived()
	EventProjected()
	EventDroppedMalformed()
	EventDroppedSlowClient()
	SubscriberAdded()

	recorder := httptest.NewRecorder()
	Handler().ServeHTTP(recorder, httptest.NewRequest(http.MethodGet, "/metrics", nil))

	if recorder.Code != http.StatusOK {
		t.Fatalf("expected 200 from /metrics, got %d", recorder.Code)
	}

	body := recorder.Body.String()
	for _, series := range []string{
		"push_kafka_events_received_total",
		"push_events_projected_total",
		`push_events_dropped_total{reason="malformed"}`,
		`push_events_dropped_total{reason="slow_client"}`,
		"push_active_subscribers",
	} {
		if !strings.Contains(body, series) {
			t.Fatalf("expected /metrics output to contain %q", series)
		}
	}
}
