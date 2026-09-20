package propagation

import (
	"context"

	"github.com/power-finance/kafka-client-go/headers"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/propagation"
)

// TextMapCarrier is the wire form of a propagated context.
type TextMapCarrier map[string]string

// InjectCurrentContext serialises the active trace context and baggage.
func InjectCurrentContext(ctx context.Context) TextMapCarrier {
	carrier := TextMapCarrier{}
	otel.GetTextMapPropagator().Inject(ctx, propagation.MapCarrier(carrier))

	return carrier
}

// InjectIntoKafkaHeaders returns the headers a produced message should carry so
// the consumer continues this trace rather than starting its own.
func InjectIntoKafkaHeaders(ctx context.Context) headers.KafkaHeaders {
	carrier := InjectCurrentContext(ctx)

	injected := make(headers.KafkaHeaders, 0, len(carrier))
	for key, value := range carrier {
		injected = append(injected, headers.String(key, value))
	}

	return injected
}
