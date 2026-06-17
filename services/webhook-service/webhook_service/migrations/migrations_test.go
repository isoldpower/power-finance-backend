package migrations

import (
	"io/fs"
	"strings"
	"testing"
)

func TestEmbeddedMigrationsArePresentAndAnnotated(t *testing.T) {
	entries, globErr := fs.Glob(FS, "*.sql")
	if globErr != nil {
		t.Fatal(globErr)
	}
	if len(entries) == 0 {
		t.Fatal("expected at least one embedded migration")
	}

	for _, name := range entries {
		content, readErr := fs.ReadFile(FS, name)
		if readErr != nil {
			t.Fatalf("read %s: %v", name, readErr)
		}

		body := string(content)
		for _, marker := range []string{"-- +goose Up", "-- +goose Down"} {
			if !strings.Contains(body, marker) {
				t.Fatalf("%s is missing the %q annotation", name, marker)
			}
		}
	}
}
