package contract

import (
	"testing"
	"time"

	"services/webhook-service/webhook_service/types"
)

func TestCursorRoundTrips(t *testing.T) {
	fingerprint := QueryFingerprint(types.DeliveryLogFilters{}, "wh-1")
	createdAt := time.Date(2026, 8, 12, 11, 51, 0, 0, time.UTC)

	anchor, decodeErr := DecodeCursor(
		EncodeCursor(DirectionNext, createdAt, "d-1", fingerprint),
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
	fingerprint := QueryFingerprint(types.DeliveryLogFilters{}, "wh-1")
	createdAt := time.Date(2026, 8, 12, 11, 51, 0, 0, time.UTC)

	anchor, decodeErr := DecodeCursor(
		EncodeCursor(DirectionPrevious, createdAt, "d-1", fingerprint),
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
	original := QueryFingerprint(types.DeliveryLogFilters{}, "wh-1")
	filtered := QueryFingerprint(types.DeliveryLogFilters{Status: "failed"}, "wh-1")
	createdAt := time.Date(2026, 8, 12, 11, 51, 0, 0, time.UTC)

	_, decodeErr := DecodeCursor(EncodeCursor(DirectionNext, createdAt, "d-1", original), filtered)
	if decodeErr != ErrCursorMismatch {
		t.Fatalf("expected a mismatch, got %v", decodeErr)
	}
}

func TestCursorFromAnotherEndpointIsRefused(t *testing.T) {
	mine := QueryFingerprint(types.DeliveryLogFilters{}, "wh-1")
	theirs := QueryFingerprint(types.DeliveryLogFilters{}, "wh-2")
	createdAt := time.Date(2026, 8, 12, 11, 51, 0, 0, time.UTC)

	_, decodeErr := DecodeCursor(EncodeCursor(DirectionNext, createdAt, "d-1", mine), theirs)
	if decodeErr != ErrCursorMismatch {
		t.Fatalf("expected a mismatch, got %v", decodeErr)
	}
}

func TestGarbageCursorIsRefused(t *testing.T) {
	fingerprint := QueryFingerprint(types.DeliveryLogFilters{}, "wh-1")

	if _, decodeErr := DecodeCursor("not-a-cursor", fingerprint); decodeErr == nil {
		t.Fatal("expected an error for an unreadable cursor")
	}
}

// TestGoldenCursorMatchesThePythonServices pins the wire format against a token
// minted by read-service, write-service and ai-service for the same position.
// A client stores one opaque token whichever service answered it, so all four
// codecs have to agree byte for byte — and this is a Go reimplementation of a
// format defined in Python, which nothing else holds together.
//
// The same two constants appear in contract_tests/cursors.py. If either side
// moves, both fail.
func TestGoldenCursorMatchesThePythonServices(t *testing.T) {
	const (
		goldenFingerprint = "1387ffe9d3754887"
		goldenToken       = "eyJ2IjoxLCJkIjoibmV4dCIsImsiOlsiMjAyNi0wOC0xMlQxMjowMDowMCswMDowMCIsIjdjM2U5YTEwLTRkMmItNGY3Ny05MWNjLTVlOGIwYTJmNmQzNCJdLCJmIjoiMTM4N2ZmZTlkMzc1NDg4NyJ9"
	)

	minted := EncodeCursor(
		DirectionNext,
		time.Date(2026, 8, 12, 12, 0, 0, 0, time.UTC),
		"7c3e9a10-4d2b-4f77-91cc-5e8b0a2f6d34",
		goldenFingerprint,
	)

	if minted != goldenToken {
		t.Fatalf(
			"cursor format drifted from the Python services:\n go:     %s\n python: %s",
			minted,
			goldenToken,
		)
	}
}

// TestTheOrderSignatureIsTheSharedOne guards the other half of a fingerprint:
// the same values under a different order signature hash differently, so a
// cursor minted here would be refused by a service that spelled it otherwise.
func TestTheOrderSignatureIsTheSharedOne(t *testing.T) {
	if OrderSignature != "created_at:desc,id:desc" {
		t.Fatalf("order signature is %q, not the shared one", OrderSignature)
	}
}
