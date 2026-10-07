package tracing

import (
	"context"

	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/baggage"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

type BaggageSpanAttributesProcessor struct {
	copiedBaggageEntryNames []string
}

func NewBaggageSpanAttributesProcessor(copiedBaggageEntryNames ...string) *BaggageSpanAttributesProcessor {
	return &BaggageSpanAttributesProcessor{
		copiedBaggageEntryNames: copiedBaggageEntryNames,
	}
}

func (processor *BaggageSpanAttributesProcessor) OnStart(parentContext context.Context, span sdktrace.ReadWriteSpan) {
	parentBaggage := baggage.FromContext(parentContext)
	for _, baggageEntryName := range processor.copiedBaggageEntryNames {
		baggageEntryValue := parentBaggage.Member(baggageEntryName).Value()
		if baggageEntryValue != "" {
			span.SetAttributes(attribute.String(baggageEntryName, baggageEntryValue))
		}
	}
}

func (processor *BaggageSpanAttributesProcessor) OnEnd(span sdktrace.ReadOnlySpan) {}

func (processor *BaggageSpanAttributesProcessor) Shutdown(ctx context.Context) error {
	return nil
}

func (processor *BaggageSpanAttributesProcessor) ForceFlush(ctx context.Context) error {
	return nil
}
