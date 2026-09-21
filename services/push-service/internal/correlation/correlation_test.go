package correlation

import (
	"context"
	"testing"
)

func TestIDRoundTripsThroughContext(t *testing.T) {
	ctx := WithID(context.Background(), "cid-1")

	correlationID, present := ID(ctx)
	if !present || correlationID != "cid-1" {
		t.Fatalf("expected cid-1 present, got %q present=%v", correlationID, present)
	}
}

func TestIDIsAbsentOnABareContext(t *testing.T) {
	if _, present := ID(context.Background()); present {
		t.Fatal("expected no correlation id on a bare context")
	}
}

func TestAnEmptyIDCountsAsAbsent(t *testing.T) {
	if _, present := ID(WithID(context.Background(), "")); present {
		t.Fatal("expected an empty correlation id to count as absent")
	}
}

func TestNewIDIsSixteenHexCharacters(t *testing.T) {
	generated := NewID()

	if len(generated) != 16 {
		t.Fatalf("expected 16 hex characters, got %q", generated)
	}
	for _, character := range generated {
		if !((character >= '0' && character <= '9') || (character >= 'a' && character <= 'f')) {
			t.Fatalf("expected lowercase hex, got %q", generated)
		}
	}
}

func TestNewIDDiffersBetweenCalls(t *testing.T) {
	if NewID() == NewID() {
		t.Fatal("expected two generated ids to differ")
	}
}

func TestLoggerIsAnnotatedWhenTheContextCarriesAnID(t *testing.T) {
	if Logger(WithID(context.Background(), "cid-1")) == nil {
		t.Fatal("expected a logger for an annotated context")
	}
	if Logger(context.Background()) == nil {
		t.Fatal("expected the default logger for a bare context")
	}
}

func TestHeaderIsTheGatewayHeaderName(t *testing.T) {
	if Header != "X-Correlation-ID" {
		t.Fatalf("unexpected correlation header %q", Header)
	}
}
