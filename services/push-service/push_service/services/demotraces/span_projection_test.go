package demotraces

import (
	"encoding/json"
	"testing"

	commonv1 "go.opentelemetry.io/proto/otlp/common/v1"
	resourcev1 "go.opentelemetry.io/proto/otlp/resource/v1"
	tracev1 "go.opentelemetry.io/proto/otlp/trace/v1"
	"google.golang.org/protobuf/proto"
)

const portfolioVisitorSession = "portfolio-visitor-session"

func stringAttribute(attributeKey string, attributeValue string) *commonv1.KeyValue {
	return &commonv1.KeyValue{
		Key:   attributeKey,
		Value: &commonv1.AnyValue{Value: &commonv1.AnyValue_StringValue{StringValue: attributeValue}},
	}
}

func encodeTracesPayload(t *testing.T, serviceName string, spans ...*tracev1.Span) []byte {
	t.Helper()

	encodedPayload, marshalErr := proto.Marshal(&tracev1.TracesData{
		ResourceSpans: []*tracev1.ResourceSpans{{
			Resource: &resourcev1.Resource{
				Attributes: []*commonv1.KeyValue{stringAttribute("service.name", serviceName)},
			},
			ScopeSpans: []*tracev1.ScopeSpans{{Spans: spans}},
		}},
	})
	if marshalErr != nil {
		t.Fatal(marshalErr)
	}

	return encodedPayload
}

func databaseInsertSpan() *tracev1.Span {
	return &tracev1.Span{
		TraceId:           []byte{0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19},
		SpanId:            []byte{0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08},
		ParentSpanId:      []byte{0x08, 0x07, 0x06, 0x05, 0x04, 0x03, 0x02, 0x01},
		Name:              "INSERT",
		Kind:              tracev1.Span_SPAN_KIND_CLIENT,
		StartTimeUnixNano: 1_700_000_000_000_000_000,
		EndTimeUnixNano:   1_700_000_000_004_500_000,
		Status:            &tracev1.Status{Code: tracev1.Status_STATUS_CODE_OK},
		Attributes: []*commonv1.KeyValue{
			stringAttribute("demo-session", portfolioVisitorSession),
			stringAttribute("db.system", "postgresql"),
			stringAttribute("db.statement", "INSERT INTO wallets (owner_email) VALUES ('private@example.com')"),
			stringAttribute("enduser.id", "user_2abc"),
		},
	}
}

func TestDemoSpanIsProjectedForItsSession(t *testing.T) {
	projectedEvents, projectErr := ProjectDemoSpanEvents(
		encodeTracesPayload(t, "write-service", databaseInsertSpan()),
	)
	if projectErr != nil {
		t.Fatal(projectErr)
	}
	if len(projectedEvents) != 1 {
		t.Fatalf("expected one projected span, got %d", len(projectedEvents))
	}

	projectedEvent := projectedEvents[0]
	if projectedEvent.UserID != portfolioVisitorSession || projectedEvent.EventType != SpanEventType {
		t.Fatalf("expected a span event keyed by the demo session, got %+v", projectedEvent)
	}

	var decodedSpan map[string]any
	if decodeErr := json.Unmarshal(projectedEvent.Payload, &decodedSpan); decodeErr != nil {
		t.Fatal(decodeErr)
	}
	expectedFields := map[string]any{
		"traceId":           "0a0b0c0d0e0f10111213141516171819",
		"spanId":            "0102030405060708",
		"parentSpanId":      "0807060504030201",
		"service":           "write-service",
		"name":              "INSERT",
		"kind":              "client",
		"status":            "ok",
		"startTimeUnixNano": "1700000000000000000",
		"durationMs":        4.5,
	}
	for fieldName, expectedValue := range expectedFields {
		if decodedSpan[fieldName] != expectedValue {
			t.Fatalf("expected %s=%v, got %v", fieldName, expectedValue, decodedSpan[fieldName])
		}
	}
}

func TestOnlyWhitelistedAttributesLeaveTheService(t *testing.T) {
	projectedEvents, _ := ProjectDemoSpanEvents(
		encodeTracesPayload(t, "write-service", databaseInsertSpan()),
	)

	var decodedSpan struct {
		Attributes map[string]any `json:"attributes"`
	}
	if decodeErr := json.Unmarshal(projectedEvents[0].Payload, &decodedSpan); decodeErr != nil {
		t.Fatal(decodeErr)
	}

	if len(decodedSpan.Attributes) != 1 || decodedSpan.Attributes["db.system"] != "postgresql" {
		t.Fatalf("expected only db.system to be forwarded, got %v", decodedSpan.Attributes)
	}
}

func TestSpanWithoutDemoSessionIsDropped(t *testing.T) {
	untaggedSpan := databaseInsertSpan()
	untaggedSpan.Attributes = []*commonv1.KeyValue{stringAttribute("db.system", "postgresql")}

	projectedEvents, projectErr := ProjectDemoSpanEvents(
		encodeTracesPayload(t, "write-service", untaggedSpan),
	)
	if projectErr != nil {
		t.Fatal(projectErr)
	}
	if len(projectedEvents) != 0 {
		t.Fatalf("expected untagged span to be dropped, got %d events", len(projectedEvents))
	}
}

func TestMalformedPayloadIsRejected(t *testing.T) {
	if _, projectErr := ProjectDemoSpanEvents([]byte{0xff, 0xff, 0xff}); projectErr == nil {
		t.Fatal("expected a malformed payload to be rejected")
	}
}

func TestDemoSessionIdentifierValidation(t *testing.T) {
	validationCases := map[string]bool{
		"f3b1c2d4-5e6f-4a7b-8c9d-0e1f2a3b4c5d": true,
		"portfolio_visitor_01":                 true,
		"GLOBAL":                               false,
		"":                                     false,
		"has spaces in the identifier":         false,
		"0123456789012345678901234567890123456789012345678901234567890123456789": false,
	}
	for candidateIdentifier, expectedValidity := range validationCases {
		if IsValidDemoSessionIdentifier(candidateIdentifier) != expectedValidity {
			t.Fatalf("expected validity %v for %q", expectedValidity, candidateIdentifier)
		}
	}
}

func projectedSpanName(t *testing.T, span *tracev1.Span) string {
	t.Helper()

	projectedEvents, projectErr := ProjectDemoSpanEvents(encodeTracesPayload(t, "write-service", span))
	if projectErr != nil {
		t.Fatal(projectErr)
	}

	var decodedSpan struct {
		Name string `json:"name"`
	}
	if decodeErr := json.Unmarshal(projectedEvents[0].Payload, &decodedSpan); decodeErr != nil {
		t.Fatal(decodeErr)
	}

	return decodedSpan.Name
}

func serverRequestSpan(spanName string, extraAttributes ...*commonv1.KeyValue) *tracev1.Span {
	return &tracev1.Span{
		TraceId:    []byte{0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19},
		SpanId:     []byte{0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08},
		Name:       spanName,
		Kind:       tracev1.Span_SPAN_KIND_SERVER,
		Attributes: append([]*commonv1.KeyValue{stringAttribute("demo-session", portfolioVisitorSession)}, extraAttributes...),
	}
}

func TestServerSpanNameIsRebuiltFromTheRouteTemplate(t *testing.T) {
	spanName := projectedSpanName(t, serverRequestSpan(
		"GET /api/v1/wallets/3f2a9c1e-0000-4000-8000-000000000001",
		stringAttribute("http.request.method", "GET"),
		stringAttribute("http.route", "api/v1/wallets/<uuid:wallet_id>"),
	))

	if spanName != "GET api/v1/wallets/<uuid:wallet_id>" {
		t.Fatalf("expected the route template, got %q", spanName)
	}
}

func TestServerSpanWithoutRouteKeepsOnlyTheMethod(t *testing.T) {
	spanName := projectedSpanName(t, serverRequestSpan(
		"GET /api/v1/wallets/3f2a9c1e-0000-4000-8000-000000000001",
		stringAttribute("http.method", "GET"),
	))

	if spanName != "GET" {
		t.Fatalf("expected only the method, got %q", spanName)
	}
}

func TestServerSpanWithoutMethodOrRouteGetsAGenericName(t *testing.T) {
	if spanName := projectedSpanName(t, serverRequestSpan("/api/v1/wallets/3f2a9c1e")); spanName != "request" {
		t.Fatalf("expected a generic name, got %q", spanName)
	}
}

func TestNonServerSpanKeepsItsName(t *testing.T) {
	if spanName := projectedSpanName(t, databaseInsertSpan()); spanName != "INSERT" {
		t.Fatalf("expected the database span name to be kept, got %q", spanName)
	}
}
