package projections

import (
	"encoding/json"
	"testing"

	"services/push-service/push_service/types"
)

func createdMessage(payload string) types.OutboxEvent {
	return types.OutboxEvent{
		EventID:       "evt-1",
		EventType:     "NotificationCreated",
		AggregateType: "notification",
		UserID:        "user_2abc",
		Payload:       []byte(payload),
	}
}

func decode(t *testing.T, raw []byte) map[string]any {
	t.Helper()

	var decoded map[string]any
	if err := json.Unmarshal(raw, &decoded); err != nil {
		t.Fatalf("payload is not JSON: %v", err)
	}

	return decoded
}

// The client prepends the notification without a follow-up request, so the
// frame has to carry the same shape one element of GET /notifications does.
func TestCreatedCarriesTheWholeResource(t *testing.T) {
	projected, err := ProjectNotificationEvents(createdMessage(`{
		"notification_id": "notif-1",
		"title": "Visa Credit near limit",
		"body": "You are at 82% of your limit.",
		"severity": "NOTIFICATION_SEVERITY_CRITICAL",
		"subject_type": "wallet",
		"subject_id": "wallet-1",
		"created_at": "2026-08-12T11:51:00Z"
	}`))
	if err != nil || len(projected) != 1 {
		t.Fatalf("expected one event, got %d (%v)", len(projected), err)
	}

	if projected[0].EventType != NotificationCreatedEvent {
		t.Fatalf("unexpected event name %q", projected[0].EventType)
	}

	resource := decode(t, projected[0].Payload)
	if resource["severity"] != "critical" {
		t.Fatalf("severity should render as the API vocabulary, got %v", resource["severity"])
	}
	if resource["acknowledged_at"] != nil || resource["updated_at"] != nil {
		t.Fatal("a new notification is unread and unedited")
	}
	subject, isObject := resource["subject"].(map[string]any)
	if !isObject || subject["type"] != "wallet" || subject["id"] != "wallet-1" {
		t.Fatalf("subject should be a followable reference, got %v", resource["subject"])
	}
}

// The SSE id doubles as the resume token, so it is the NOTIFICATION id rather
// than the outbox event id the message arrived under.
func TestCreatedUsesTheNotificationIdAsTheResumeToken(t *testing.T) {
	projected, _ := ProjectNotificationEvents(createdMessage(
		`{"notification_id":"notif-1","created_at":"2026-08-12T11:51:00Z"}`,
	))

	if projected[0].EventID != "notif-1" {
		t.Fatalf("expected the notification id, got %q", projected[0].EventID)
	}
}

// A reference needs both halves to be followable, so half of one is null.
func TestCreatedWithoutASubjectSendsNull(t *testing.T) {
	projected, _ := ProjectNotificationEvents(createdMessage(
		`{"notification_id":"notif-1","subject_type":"wallet","subject_id":""}`,
	))

	if decode(t, projected[0].Payload)["subject"] != nil {
		t.Fatal("a half-filled subject should be null")
	}
}

// An unknown or unspecified severity renders as `info` rather than dropping the
// notification the client is waiting for.
func TestAnUnknownSeverityDegradesToInfo(t *testing.T) {
	projected, _ := ProjectNotificationEvents(createdMessage(
		`{"notification_id":"notif-1","severity":"NOTIFICATION_SEVERITY_UNSPECIFIED"}`,
	))

	if decode(t, projected[0].Payload)["severity"] != "info" {
		t.Fatal("unspecified severity should read as info")
	}
}

func TestCreatedWithoutAnIdIsRejected(t *testing.T) {
	if _, err := ProjectNotificationEvents(createdMessage(`{"title":"orphan"}`)); err == nil {
		t.Fatal("an event with no notification id has no resume token and cannot be sent")
	}
}

// A client tracks notifications individually and has no use for the batch a
// second device happened to acknowledge them in.
func TestAcknowledgedFansOutOnePerId(t *testing.T) {
	projected, err := ProjectNotificationEvents(types.OutboxEvent{
		EventID:   "evt-2",
		EventType: "NotificationsAcknowledged",
		UserID:    "user_2abc",
		Payload: []byte(`{
			"notification_ids": ["notif-1", "notif-2"],
			"acknowledged_at": "2026-08-12T12:02:00Z"
		}`),
	})
	if err != nil || len(projected) != 2 {
		t.Fatalf("expected one event per id, got %d (%v)", len(projected), err)
	}

	for index, expectedID := range []string{"notif-1", "notif-2"} {
		if projected[index].EventType != NotificationAcknowledgedEvent {
			t.Fatalf("unexpected event name %q", projected[index].EventType)
		}
		if projected[index].EventID != expectedID {
			t.Fatalf("expected id %q, got %q", expectedID, projected[index].EventID)
		}
	}
}

// Deliberately thin: the id and the new timestamp are the only things that
// changed, so the frame carries nothing else.
func TestAcknowledgedIsThin(t *testing.T) {
	projected, _ := ProjectNotificationEvents(types.OutboxEvent{
		EventType: "NotificationsAcknowledged",
		Payload: []byte(
			`{"notification_ids":["notif-1"],"acknowledged_at":"2026-08-12T12:02:00Z"}`,
		),
	})

	resource := decode(t, projected[0].Payload)
	if len(resource) != 2 {
		t.Fatalf("expected only id and acknowledged_at, got %v", resource)
	}
	if resource["acknowledged_at"] != "2026-08-12T12:02:00Z" {
		t.Fatalf("unexpected timestamp %v", resource["acknowledged_at"])
	}
}

func TestMalformedPayloadIsReportedRatherThanForwarded(t *testing.T) {
	if _, err := ProjectNotificationEvents(createdMessage(`not json`)); err == nil {
		t.Fatal("expected a decode error")
	}
}
