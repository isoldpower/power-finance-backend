package tracing

import (
	"context"
	"fmt"
	"strings"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.27.0"
)

const shutdownTimeout = 5 * time.Second

type ShutdownFunc func(ctx context.Context) error

func Configure(ctx context.Context, defaultServiceName string) (Settings, ShutdownFunc, error) {
	settings := ResolveSettings(defaultServiceName)
	installPropagators()

	if !settings.IsEnabled {
		return settings, noopShutdown, nil
	}

	exporter, exporterErr := otlptracegrpc.New(
		ctx,
		otlptracegrpc.WithEndpoint(stripScheme(settings.ExporterEndpoint)),
		otlptracegrpc.WithInsecure(),
	)
	if exporterErr != nil {
		returnError := fmt.Errorf("tracing: otlp exporter: %w", exporterErr)
		return settings, noopShutdown, returnError
	}

	tracerProvider := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithSampler(buildSampler(settings.SamplerRatio)),
		sdktrace.WithResource(buildResource(settings)),
	)
	otel.SetTracerProvider(tracerProvider)
	return settings, tracerProvider.Shutdown, nil
}

func installPropagators() {
	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(
		propagation.TraceContext{},
		propagation.Baggage{},
	))
}

func buildSampler(samplerRatio float64) sdktrace.Sampler {
	if samplerRatio >= 1.0 {
		return sdktrace.ParentBased(sdktrace.AlwaysSample())
	}

	return sdktrace.ParentBased(sdktrace.TraceIDRatioBased(samplerRatio))
}

func buildResource(settings Settings) *resource.Resource {
	return resource.NewWithAttributes(
		semconv.SchemaURL,
		semconv.ServiceName(settings.ServiceName),
		semconv.DeploymentEnvironmentName(settings.DeploymentEnvironment),
	)
}

func stripScheme(endpoint string) string {
	withoutScheme := strings.TrimPrefix(
		strings.TrimPrefix(endpoint, "http://"),
		"https://",
	)

	return strings.TrimSuffix(withoutScheme, "/")
}

func noopShutdown(ctx context.Context) error {
	return nil
}

func ShutdownTimeout() time.Duration {
	return shutdownTimeout
}
