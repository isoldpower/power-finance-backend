package correlation

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"log/slog"
)

// Header carries the gateway-issued request correlation id.
const Header = "X-Correlation-ID"

type contextKey struct{}

// WithID returns a context with pre-populated Correlation-ID value.
func WithID(parent context.Context, correlationID string) context.Context {
	return context.WithValue(parent, contextKey{}, correlationID)
}

// ID retrieves Correlation-ID value from context populated by WithID.
func ID(ctx context.Context) (string, bool) {
	correlationID, present := ctx.Value(contextKey{}).(string)

	return correlationID, present && correlationID != ""
}

// NewID generates a random fallback id for requests without the gateway header.
func NewID() string {
	buffer := make([]byte, 8)
	if _, readErr := rand.Read(buffer); readErr != nil {
		return "unknown"
	}

	return hex.EncodeToString(buffer)
}

// Logger returns the default logger annotated with the context's correlation id.
func Logger(ctx context.Context) *slog.Logger {
	if correlationID, present := ID(ctx); present {
		return slog.With("correlation_id", correlationID)
	}

	return slog.Default()
}
