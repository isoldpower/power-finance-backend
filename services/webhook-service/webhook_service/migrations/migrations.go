package migrations

import "embed"

// FS holds the Goose SQL migration files embedded into the binary so the
// migrate command needs no on-disk migrations directory at runtime.
//
//go:embed *.sql
var FS embed.FS
