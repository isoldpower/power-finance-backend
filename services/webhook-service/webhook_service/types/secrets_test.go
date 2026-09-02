package types

import (
	"testing"
	"time"
)

func graceWindow(base time.Time) EndpointSecrets {
	expiry := base.Add(24 * time.Hour)

	return EndpointSecrets{
		Secret:                  "new",
		SecretVersion:           2,
		PreviousSecret:          "old",
		PreviousSecretVersion:   1,
		PreviousSecretExpiresAt: &expiry,
	}
}

func TestCurrentVersionSignsWithTheLiveSecret(t *testing.T) {
	now := time.Now().UTC()

	if got := graceWindow(now).For(2, now); got != "new" {
		t.Fatalf("expected the live secret, got %q", got)
	}
}

// The whole point of the window: a delivery enqueued before the rotation is
// still signed with the secret its receiver was verifying against.
func TestInFlightDeliveryKeepsTheReplacedSecret(t *testing.T) {
	now := time.Now().UTC()

	if got := graceWindow(now).For(1, now); got != "old" {
		t.Fatalf("expected the replaced secret inside the window, got %q", got)
	}
}

func TestExpiredWindowFallsBackToTheLiveSecret(t *testing.T) {
	now := time.Now().UTC()

	if got := graceWindow(now).For(1, now.Add(25*time.Hour)); got != "new" {
		t.Fatalf("expected the live secret once the window closed, got %q", got)
	}
}

// A third rotation drops the oldest secret, so a delivery pinned to it has
// nothing to fall back on but the live secret.
func TestVersionOlderThanThePreviousOneUsesTheLiveSecret(t *testing.T) {
	now := time.Now().UTC()

	if got := graceWindow(now).For(0, now); got != "new" {
		t.Fatalf("expected the live secret, got %q", got)
	}
}

func TestEndpointWithNoRotationAlwaysSignsWithItsOnlySecret(t *testing.T) {
	now := time.Now().UTC()
	secrets := EndpointSecrets{Secret: "only", SecretVersion: 1}

	if got := secrets.For(1, now); got != "only" {
		t.Fatalf("expected the only secret, got %q", got)
	}
	if got := secrets.For(7, now); got != "only" {
		t.Fatalf("an unknown version must still send, got %q", got)
	}
}
