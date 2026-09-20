package propagation

import (
	"context"

	"go.opentelemetry.io/otel/baggage"
)

// ReadBaggageEntry returns the value of one W3C baggage entry on the context,
// empty when it is absent.
func ReadBaggageEntry(ctx context.Context, entryName string) string {
	return baggage.FromContext(ctx).Member(entryName).Value()
}

// WriteBaggageEntry returns a context carrying one additional baggage entry.
func WriteBaggageEntry(ctx context.Context, entryName string, entryValue string) context.Context {
	member, memberErr := baggage.NewMember(entryName, entryValue)
	if memberErr != nil {
		return ctx
	}

	updated, updateErr := baggage.FromContext(ctx).SetMember(member)
	if updateErr != nil {
		return ctx
	}

	return baggage.ContextWithBaggage(ctx, updated)
}
