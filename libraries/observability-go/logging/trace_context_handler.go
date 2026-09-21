package logging

import (
	"context"
	"log/slog"

	"github.com/power-finance/observability-go/sandbox"
	"github.com/power-finance/observability-go/tracing"
)

const (
	TraceIDField   = "trace_id"
	SpanIDField    = "span_id"
	SandboxIDField = "sandbox_id"

	MissingValuePlaceholder = "-"
)

// TraceContextHandler stamps trace, span and sandbox ids onto every record.
type TraceContextHandler struct {
	inner slog.Handler
}

func NewTraceContextHandler(inner slog.Handler) TraceContextHandler {
	return TraceContextHandler{inner: inner}
}

func (h TraceContextHandler) Enabled(ctx context.Context, level slog.Level) bool {
	return h.inner.Enabled(ctx, level)
}

func (h TraceContextHandler) Handle(ctx context.Context, record slog.Record) error {
	record.AddAttrs(
		slog.String(TraceIDField, orPlaceholder(tracing.CurrentTraceIDHex(ctx))),
		slog.String(SpanIDField, orPlaceholder(tracing.CurrentSpanIDHex(ctx))),
		slog.String(SandboxIDField, orPlaceholder(sandbox.CurrentID(ctx))),
	)

	return h.inner.Handle(ctx, record)
}

func (h TraceContextHandler) WithAttrs(attrs []slog.Attr) slog.Handler {
	return NewTraceContextHandler(h.inner.WithAttrs(attrs))
}

func (h TraceContextHandler) WithGroup(name string) slog.Handler {
	return NewTraceContextHandler(h.inner.WithGroup(name))
}

func orPlaceholder(value string) string {
	if value == "" {
		return MissingValuePlaceholder
	}

	return value
}
