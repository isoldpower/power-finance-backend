package logging

import (
	"bytes"
	"context"
	"encoding/json"
	"log/slog"
	"testing"

	"github.com/power-finance/observability-go/sandbox"
)

func handlerWithBuffer() (*bytes.Buffer, slog.Handler) {
	buffer := &bytes.Buffer{}

	return buffer, NewTraceContextHandler(slog.NewJSONHandler(buffer, nil))
}

func loggedFields(t *testing.T, buffer *bytes.Buffer) map[string]any {
	t.Helper()

	fields := map[string]any{}
	if decodeErr := json.Unmarshal(buffer.Bytes(), &fields); decodeErr != nil {
		t.Fatalf("could not decode log line %q: %v", buffer.String(), decodeErr)
	}

	return fields
}

func TestBareContextLogsPlaceholders(t *testing.T) {
	buffer, handler := handlerWithBuffer()
	slog.New(handler).InfoContext(context.Background(), "hello")

	fields := loggedFields(t, buffer)
	for _, field := range []string{TraceIDField, SpanIDField, SandboxIDField} {
		if fields[field] != MissingValuePlaceholder {
			t.Fatalf("expected %s to be %q, got %v", field, MissingValuePlaceholder, fields[field])
		}
	}
}

func TestSandboxIDIsTakenFromBaggage(t *testing.T) {
	buffer, handler := handlerWithBuffer()
	ctx := sandbox.AttachID(context.Background(), "nikita")

	slog.New(handler).InfoContext(ctx, "hello")

	if fields := loggedFields(t, buffer); fields[SandboxIDField] != "nikita" {
		t.Fatalf("expected nikita, got %v", fields[SandboxIDField])
	}
}

func TestAttributesAddedByTheCallerSurvive(t *testing.T) {
	buffer, handler := handlerWithBuffer()

	slog.New(handler).With("component", "consumer").InfoContext(context.Background(), "hello")

	fields := loggedFields(t, buffer)
	if fields["component"] != "consumer" {
		t.Fatalf("expected the caller attribute to survive, got %v", fields["component"])
	}
	if fields[TraceIDField] != MissingValuePlaceholder {
		t.Fatalf("expected the trace field to still be stamped, got %v", fields[TraceIDField])
	}
}

func TestLevelFilteringIsDelegatedToTheInnerHandler(t *testing.T) {
	buffer := &bytes.Buffer{}
	inner := slog.NewJSONHandler(buffer, &slog.HandlerOptions{Level: slog.LevelWarn})
	handler := NewTraceContextHandler(inner)

	if handler.Enabled(context.Background(), slog.LevelDebug) {
		t.Fatal("expected debug to be filtered out by the inner handler")
	}
	if !handler.Enabled(context.Background(), slog.LevelError) {
		t.Fatal("expected error to pass the inner handler")
	}
}
