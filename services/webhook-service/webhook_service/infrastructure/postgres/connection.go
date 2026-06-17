package postgres

import (
	"context"
	"fmt"

	"github.com/jackc/pgx/v5/pgxpool"
)

// Connect opens a pgx connection pool and verifies connectivity, failing fast
// when the store is unreachable.
func Connect(ctx context.Context, dsn string) (*pgxpool.Pool, error) {
	pool, poolErr := pgxpool.New(ctx, dsn)
	if poolErr != nil {
		return nil, fmt.Errorf("postgres: open pool: %w", poolErr)
	}

	if pingErr := pool.Ping(ctx); pingErr != nil {
		pool.Close()
		return nil, fmt.Errorf("postgres: ping: %w", pingErr)
	}

	return pool, nil
}
