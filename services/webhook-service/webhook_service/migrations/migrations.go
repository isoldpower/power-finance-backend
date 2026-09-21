package migrations

import "embed"

// FS holds the Goose SQL migrations embedded into the binary.
//
//go:embed *.sql
var FS embed.FS
