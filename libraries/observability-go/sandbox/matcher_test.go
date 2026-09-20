package sandbox

import "testing"

func TestBaselineMatcherOwnsUntaggedTrafficOnly(t *testing.T) {
	matcher := NewTrafficMatcher("")

	if !matcher.IsBaseline() {
		t.Fatal("expected baseline matcher")
	}
	if !matcher.IsOwnedTraffic("") {
		t.Fatal("baseline should own untagged traffic")
	}
	if matcher.IsOwnedTraffic("nikita") {
		t.Fatal("baseline should not own a sandbox's traffic")
	}
}

func TestSandboxMatcherOwnsItsOwnTrafficOnly(t *testing.T) {
	matcher := NewTrafficMatcher("nikita")

	if matcher.IsBaseline() {
		t.Fatal("expected non-baseline matcher")
	}
	if !matcher.IsOwnedTraffic("nikita") {
		t.Fatal("sandbox should own its own traffic")
	}
	if matcher.IsOwnedTraffic("") {
		t.Fatal("sandbox should not own baseline traffic")
	}
	if matcher.IsOwnedTraffic("anna") {
		t.Fatal("sandbox should not own another sandbox's traffic")
	}
}
