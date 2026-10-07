package tracing

import (
	"context"
	"testing"

	"github.com/power-finance/observability-go/demosession"
	"github.com/power-finance/observability-go/propagation"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	"go.opentelemetry.io/otel/sdk/trace/tracetest"
)

func newDemoSessionTracerProvider() (*sdktrace.TracerProvider, *tracetest.InMemoryExporter) {
	finishedSpanExporter := tracetest.NewInMemoryExporter()
	tracerProvider := sdktrace.NewTracerProvider(
		sdktrace.WithSpanProcessor(NewBaggageSpanAttributesProcessor(demosession.BaggageEntryName)),
		sdktrace.WithSyncer(finishedSpanExporter),
	)

	return tracerProvider, finishedSpanExporter
}

func readSpanAttribute(span tracetest.SpanStub, attributeName string) (string, bool) {
	for _, keyValue := range span.Attributes {
		if string(keyValue.Key) == attributeName {
			return keyValue.Value.AsString(), true
		}
	}

	return "", false
}

func TestSpanStartedUnderDemoBaggageCarriesTheSessionAttribute(t *testing.T) {
	tracerProvider, finishedSpanExporter := newDemoSessionTracerProvider()
	tracer := tracerProvider.Tracer("baggage-span-attributes-tests")

	demoContext := propagation.WriteBaggageEntry(
		context.Background(),
		demosession.BaggageEntryName,
		"portfolio-visitor-session",
	)
	parentContext, parentSpan := tracer.Start(demoContext, "notifications fanout consume")
	_, childSpan := tracer.Start(parentContext, "sse write")
	childSpan.End()
	parentSpan.End()

	finishedSpans := finishedSpanExporter.GetSpans()
	if len(finishedSpans) != 2 {
		t.Fatalf("expected 2 finished spans, got %d", len(finishedSpans))
	}
	for _, finishedSpan := range finishedSpans {
		sessionValue, present := readSpanAttribute(finishedSpan, demosession.SpanAttributeName)
		if !present || sessionValue != "portfolio-visitor-session" {
			t.Fatalf("expected span %q to carry the demo session, got %q/%v", finishedSpan.Name, sessionValue, present)
		}
	}
}

func TestSpanWithoutDemoBaggageCarriesNoSessionAttribute(t *testing.T) {
	tracerProvider, finishedSpanExporter := newDemoSessionTracerProvider()

	_, span := tracerProvider.Tracer("baggage-span-attributes-tests").Start(context.Background(), "plain request")
	span.End()

	finishedSpans := finishedSpanExporter.GetSpans()
	if _, present := readSpanAttribute(finishedSpans[0], demosession.SpanAttributeName); present {
		t.Fatal("expected no demo session attribute without baggage")
	}
}
