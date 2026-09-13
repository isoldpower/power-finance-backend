package propagation

import (
	"context"

	"github.com/power-finance/kafka-client-go/headers"
	"go.opentelemetry.io/otel"
)

func ExtractFromKafkaHeaders(ctx context.Context, kafkaHeaders headers.KafkaHeaders) context.Context {
	return otel.GetTextMapPropagator().Extract(ctx, NewKafkaHeaderCarrier(kafkaHeaders))
}
