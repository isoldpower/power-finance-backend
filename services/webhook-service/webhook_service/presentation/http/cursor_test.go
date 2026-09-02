package http

import (
	"testing"
	"time"

	"services/webhook-service/webhook_service/types"
)

func TestCursorRoundTrips(t *testing.T) {
	fingerprint := queryFingerprint(types.DeliveryLogFilters{}, "wh-1")
	createdAt := time.Date(2026, 8, 12, 11, 51, 0, 0, time.UTC)

	anchor, decodeErr := decodeCursor(
		encodeCursor(directionNext, createdAt, "d-1", fingerprint),
		fingerprint,
	)
	if decodeErr != nil {
		t.Fatalf("round trip failed: %v", decodeErr)
	}
	if !anchor.CreatedAt.Equal(createdAt) || anchor.ID != "d-1" || anchor.Backwards {
		t.Fatalf("anchor not preserved: %+v", anchor)
	}
}

func TestBackwardCursorDecodesAsBackwards(t *testing.T) {
	fingerprint := queryFingerprint(types.DeliveryLogFilters{}, "wh-1")
	createdAt := time.Date(2026, 8, 12, 11, 51, 0, 0, time.UTC)

	anchor, decodeErr := decodeCursor(
		encodeCursor(directionPrevious, createdAt, "d-1", fingerprint),
		fingerprint,
	)
	if decodeErr != nil {
		t.Fatalf("round trip failed: %v", decodeErr)
	}
	if !anchor.Backwards {
		t.Fatal("prev cursor should decode as a backward scan")
	}
}

// Carrying a cursor across a filter change would silently skip or repeat rows,
// so the cursor is bound to the query that produced it.
func TestCursorFromAnotherQueryIsRefused(t *testing.T) {
	original := queryFingerprint(types.DeliveryLogFilters{}, "wh-1")
	filtered := queryFingerprint(types.DeliveryLogFilters{Status: "failed"}, "wh-1")
	createdAt := time.Date(2026, 8, 12, 11, 51, 0, 0, time.UTC)

	_, decodeErr := decodeCursor(encodeCursor(directionNext, createdAt, "d-1", original), filtered)
	if decodeErr != errCursorMismatch {
		t.Fatalf("expected a mismatch, got %v", decodeErr)
	}
}

func TestCursorFromAnotherEndpointIsRefused(t *testing.T) {
	mine := queryFingerprint(types.DeliveryLogFilters{}, "wh-1")
	theirs := queryFingerprint(types.DeliveryLogFilters{}, "wh-2")
	createdAt := time.Date(2026, 8, 12, 11, 51, 0, 0, time.UTC)

	_, decodeErr := decodeCursor(encodeCursor(directionNext, createdAt, "d-1", mine), theirs)
	if decodeErr != errCursorMismatch {
		t.Fatalf("expected a mismatch, got %v", decodeErr)
	}
}

func TestGarbageCursorIsRefused(t *testing.T) {
	fingerprint := queryFingerprint(types.DeliveryLogFilters{}, "wh-1")

	if _, decodeErr := decodeCursor("not-a-cursor", fingerprint); decodeErr == nil {
		t.Fatal("expected an error for an unreadable cursor")
	}
}
