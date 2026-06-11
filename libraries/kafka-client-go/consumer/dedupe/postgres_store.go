package dedupe

import (
	"context"
	"errors"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
)

type PostgresExecutor interface {
	Exec(ctx context.Context, sql string, arguments ...any) (pgconn.CommandTag, error)
}

type PostgresQuerier interface {
	PostgresExecutor
	QueryRow(ctx context.Context, sql string, args ...any) pgx.Row
}

type markSettings struct {
	executor   PostgresExecutor
	consumedAt time.Time
}

type MarkOption func(*markSettings)

func WithMarkExecutor(executor PostgresExecutor) MarkOption {
	return func(settings *markSettings) {
		settings.executor = executor
	}
}

func WithMarkConsumedAt(consumedAt time.Time) MarkOption {
	return func(settings *markSettings) {
		settings.consumedAt = consumedAt
	}
}

type PostgresStore struct {
	querier       PostgresQuerier
	consumerGroup string
	table         string

	selectSeenEvent     string
	insertConsumedEvent string
}

type PostgresStoreOption func(*PostgresStore)

func WithTable(table string) PostgresStoreOption {
	return func(store *PostgresStore) {
		store.table = table
	}
}

func NewPostgresStore(
	querier PostgresQuerier,
	consumerGroup string,
	options ...PostgresStoreOption,
) *PostgresStore {
	store := &PostgresStore{
		querier:       querier,
		consumerGroup: consumerGroup,
		table:         defaultTable,
	}

	for _, applyOption := range options {
		applyOption(store)
	}
	store.selectSeenEvent = getSelectSeenEventTemplateSQL(store.table)
	store.insertConsumedEvent = getInsertConsumedEventTemplateSQL(store.table)

	return store
}

func (s *PostgresStore) Seen(ctx context.Context, eventID string) (bool, error) {
	var matchedRow int
	scanErr := s.querier.
		QueryRow(ctx, s.selectSeenEvent, s.consumerGroup, eventID).
		Scan(&matchedRow)

	if errors.Is(scanErr, pgx.ErrNoRows) {
		return false, nil
	} else if scanErr != nil {
		return false, scanErr
	}

	return true, nil
}

func (s *PostgresStore) Mark(
	ctx context.Context,
	eventID string,
	options ...MarkOption,
) error {
	settings := markSettings{
		executor:   s.querier,
		consumedAt: time.Now().UTC(),
	}
	for _, applyOption := range options {
		applyOption(&settings)
	}

	_, execErr := settings.executor.Exec(
		ctx,
		s.insertConsumedEvent,
		s.consumerGroup,
		eventID,
		settings.consumedAt,
	)

	return execErr
}
