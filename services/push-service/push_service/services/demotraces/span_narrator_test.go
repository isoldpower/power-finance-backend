package demotraces

import (
	"encoding/json"
	"strings"
	"testing"

	commonv1 "go.opentelemetry.io/proto/otlp/common/v1"
	tracev1 "go.opentelemetry.io/proto/otlp/trace/v1"
)

func loadEmbeddedSpanNarrator(t *testing.T) *SpanNarrator {
	t.Helper()

	spanNarrator, narratorErr := NewSpanNarrator()
	if narratorErr != nil {
		t.Fatalf("embedded span narratives are invalid: %v", narratorErr)
	}

	return spanNarrator
}

func TestEmbeddedNarrativesDescribeRealSpansFromTheRetest(t *testing.T) {
	spanNarrator := loadEmbeddedSpanNarrator(t)

	narrativeCases := []struct {
		caseName          string
		span              projectedSpan
		expectedNarrative string
	}{
		{
			caseName: "gateway root span",
			span: projectedSpan{ServiceName: "api-gateway", Kind: "server", Name: "POST /api/v1", DurationMilliseconds: 555.8,
				Attributes: map[string]any{"http.method": "POST", "http.route": "/api/v1", "http.status_code": int64(201)}},
			expectedNarrative: "The API gateway received POST /api/v1 and answered 201 after 555.8 ms.",
		},
		{
			caseName:          "clerk token verification",
			span:              projectedSpan{ServiceName: "api-gateway", Kind: "internal", Name: "kong.access.plugin.clerk-jwt", DurationMilliseconds: 364.7},
			expectedNarrative: "The gateway verified the Clerk session token in 364.7 ms.",
		},
		{
			caseName:          "plugin without a dedicated rule",
			span:              projectedSpan{ServiceName: "api-gateway", Kind: "internal", Name: "kong.access.plugin.acl", DurationMilliseconds: 0.2},
			expectedNarrative: "The gateway ran its acl plugin in 0.20 ms.",
		},
		{
			caseName:          "balancer",
			span:              projectedSpan{ServiceName: "api-gateway", Kind: "client", Name: "kong.balancer", DurationMilliseconds: 143.6},
			expectedNarrative: "The gateway forwarded the request to the upstream service, which took 143.6 ms to respond.",
		},
		{
			caseName: "response headers sent",
			span: projectedSpan{ServiceName: "write-service", Kind: "internal", Name: "POST http send",
				Attributes: map[string]any{"http.status_code": int64(201)}},
			expectedNarrative: "write-service sent the response headers with status 201.",
		},
		{
			caseName:          "response body sent",
			span:              projectedSpan{ServiceName: "write-service", Kind: "internal", Name: "POST http send", Attributes: map[string]any{}},
			expectedNarrative: "write-service sent the response body.",
		},
		{
			caseName: "django view",
			span: projectedSpan{ServiceName: "write-service", Kind: "internal", Name: "POST api/v1/wallets", DurationMilliseconds: 137.6,
				Attributes: map[string]any{"http.method": "POST", "http.route": "api/v1/wallets", "http.status_code": int64(201)}},
			expectedNarrative: "write-service ran its POST api/v1/wallets handler in 137.6 ms.",
		},
		{
			caseName: "postgres insert",
			span: projectedSpan{ServiceName: "write-service", Kind: "client", Name: "INSERT", DurationMilliseconds: 1.7,
				Attributes: map[string]any{"db.system": "postgresql", "db.name": "power_finance_write"}},
			expectedNarrative: "write-service inserted rows into Postgres database power_finance_write in 1.7 ms.",
		},
		{
			caseName: "immudb append",
			span: projectedSpan{ServiceName: "write-service", Kind: "client", Name: "sqlExec", DurationMilliseconds: 32.5,
				Attributes: map[string]any{"db.system": "immudb", "db.name": "transactions", "db.operation": "sqlExec"}},
			expectedNarrative: "write-service appended to the tamper-evident ImmuDB ledger transactions in 32.5 ms.",
		},
		{
			caseName: "redis cache invalidation",
			span: projectedSpan{ServiceName: "read-write-consumer", Kind: "client", Name: "INCRBY", DurationMilliseconds: 10,
				Attributes: map[string]any{"db.system": "redis"}},
			expectedNarrative: "read-write-consumer bumped a cache version counter in Redis, which invalidates cached responses.",
		},
		{
			caseName: "elasticsearch update over a second",
			span: projectedSpan{ServiceName: "read-write-consumer", Kind: "internal", Name: "update", DurationMilliseconds: 1966.7,
				Attributes: map[string]any{"db.system": "elasticsearch", "db.operation": "update", "http.request.method": "POST"}},
			expectedNarrative: "read-write-consumer updated a document in Elasticsearch in 1.97 s.",
		},
		{
			caseName: "push fanout",
			span: projectedSpan{ServiceName: "push-service", Kind: "consumer", Name: "notifications fanout consume",
				Attributes: map[string]any{"messaging.destination.name": "events.async"}},
			expectedNarrative: "push-service received an event from events.async and pushed it to the user's open browser tabs.",
		},
		{
			caseName: "flink scoring",
			span: projectedSpan{ServiceName: "antifraud-taskmanager", Kind: "consumer", Name: "events.async process", DurationMilliseconds: 9,
				Attributes: map[string]any{"messaging.destination.name": "events.async", "messaging.system": "kafka"}},
			expectedNarrative: "The Flink antifraud job scored an event from events.async in 9.0 ms.",
		},
		{
			caseName:          "catch-all for an unknown span",
			span:              projectedSpan{ServiceName: "ai-dispatcher", Kind: "internal", Name: "reconcile", DurationMilliseconds: 4.2, Attributes: map[string]any{}},
			expectedNarrative: "ai-dispatcher ran reconcile in 4.2 ms.",
		},
	}

	for _, narrativeCase := range narrativeCases {
		t.Run(narrativeCase.caseName, func(t *testing.T) {
			if narrative := spanNarrator.Describe(narrativeCase.span); narrative != narrativeCase.expectedNarrative {
				t.Fatalf("expected %q, got %q", narrativeCase.expectedNarrative, narrative)
			}
		})
	}
}

func TestRuleWithMissingPlaceholderFallsThroughToTheNextRule(t *testing.T) {
	spanNarrator := loadEmbeddedSpanNarrator(t)

	narrative := spanNarrator.Describe(projectedSpan{
		ServiceName:          "api-gateway",
		Kind:                 "server",
		Name:                 "request",
		DurationMilliseconds: 12.3,
		Attributes:           map[string]any{},
	})

	if narrative != "The API gateway handled the request in 12.3 ms." {
		t.Fatalf("expected the fallback gateway narrative, got %q", narrative)
	}
}

func TestFailedSpanNarrativeSaysItFailed(t *testing.T) {
	spanNarrator := loadEmbeddedSpanNarrator(t)

	narrative := spanNarrator.Describe(projectedSpan{
		ServiceName:          "write-service",
		Kind:                 "client",
		Name:                 "sqlExec",
		Status:               "error",
		DurationMilliseconds: 3000,
		Attributes:           map[string]any{"db.system": "immudb", "db.name": "transactions"},
	})

	if !strings.HasSuffix(narrative, " It failed.") {
		t.Fatalf("expected the failure to be stated, got %q", narrative)
	}
}

func TestInvalidNarrativeDocumentsAreRejected(t *testing.T) {
	invalidDocuments := map[string]string{
		"malformed JSON":          `not json`,
		"unknown field":           `{"version":1,"rules":[{"match":{},"template":"{service}","priority":1}]}`,
		"no rules":                `{"version":1,"rules":[]}`,
		"empty template":          `{"version":1,"rules":[{"match":{},"template":"  "}]}`,
		"unknown placeholder":     `{"version":1,"rules":[{"match":{"kind":"server"},"template":"{host}"},{"match":{},"template":"{service}"}]}`,
		"empty attribute name":    `{"version":1,"rules":[{"match":{"kind":"server"},"template":"{attr:a|}"},{"match":{},"template":"{service}"}]}`,
		"no catch-all rule":       `{"version":1,"rules":[{"match":{"kind":"server"},"template":"{service}"}]}`,
		"catch-all needs a value": `{"version":1,"rules":[{"match":{},"template":"{attr:db.name}"}]}`,
	}

	for documentName, invalidDocument := range invalidDocuments {
		t.Run(documentName, func(t *testing.T) {
			if _, parseErr := parseSpanNarrator([]byte(invalidDocument)); parseErr == nil {
				t.Fatalf("expected %s to be rejected", documentName)
			}
		})
	}
}

func TestProjectedSpanCarriesItsNarrative(t *testing.T) {
	spanNarrator := loadEmbeddedSpanNarrator(t)

	projectedEvents, projectErr := ProjectDemoSpanEvents(
		encodeTracesPayload(t, "write-service", databaseInsertSpan()),
		SpanProjectionPolicy{IsKnownService: isWriteService, Narrator: spanNarrator},
	)
	if projectErr != nil {
		t.Fatal(projectErr)
	}

	var decodedSpan struct {
		Narrative string `json:"narrative"`
	}
	if decodeErr := json.Unmarshal(projectedEvents[0].Payload, &decodedSpan); decodeErr != nil {
		t.Fatal(decodeErr)
	}

	if decodedSpan.Narrative != "write-service called INSERT in 4.5 ms." {
		t.Fatalf("expected the client fallback narrative for a span without db.name, got %q", decodedSpan.Narrative)
	}
}

func TestAsgiMessageSpanNamesDropTheRawPath(t *testing.T) {
	asgiSendSpan := &tracev1.Span{
		Name: "PATCH /api/v1/wallets/3f2a9c1e-0000-4000-8000-000000000001 http send",
		Kind: tracev1.Span_SPAN_KIND_INTERNAL,
		Attributes: []*commonv1.KeyValue{
			stringAttribute("demo-session", portfolioVisitorSession),
		},
	}

	if spanName := projectedSpanName(t, asgiSendSpan); spanName != "PATCH http send" {
		t.Fatalf("expected the raw path to be removed, got %q", spanName)
	}
}
