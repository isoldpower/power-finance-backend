package services

import (
	"regexp"
	"testing"
)

var uuidV4Pattern = regexp.MustCompile(`^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`)

func TestNewUUIDIsV4Formatted(t *testing.T) {
	id := newUUID()
	if !uuidV4Pattern.MatchString(id) {
		t.Fatalf("newUUID() = %q, not a v4 UUID", id)
	}
}

func TestNewUUIDIsUnique(t *testing.T) {
	seen := make(map[string]struct{}, 1000)
	for range 1000 {
		id := newUUID()
		if _, dup := seen[id]; dup {
			t.Fatalf("newUUID produced a duplicate: %q", id)
		}
		seen[id] = struct{}{}
	}
}
