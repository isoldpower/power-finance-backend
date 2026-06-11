package dedupe

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"testing"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"

	kafkaclient "github.com/power-finance/kafka-client-go"
	"github.com/power-finance/kafka-client-go/headers"
)

func fakeMessage() kafkaclient.ConsumedMessage {
	return kafkaclient.ConsumedMessage{
		Topic:   "events.async",
		Key:     []byte("acct-1"),
		Value:   []byte("payload"),
		Headers: headers.KafkaHeaders{},
	}
}

func TestInMemoryStoreSeenAfterMark(t *testing.T) {
	store := NewInMemoryStore()

	seenBeforeMark, err := store.Seen(context.Background(), "evt-1")
	if err != nil {
		t.Fatal(err)
	}
	if seenBeforeMark {
		t.Fatal("expected unseen before mark")
	}

	if err := store.Mark(context.Background(), "evt-1"); err != nil {
		t.Fatal(err)
	}

	seenAfterMark, err := store.Seen(context.Background(), "evt-1")
	if err != nil {
		t.Fatal(err)
	}
	if !seenAfterMark {
		t.Fatal("expected seen after mark")
	}
}

func TestGateDisabledWithoutStoreOrExtractor(t *testing.T) {
	extractor := func(message kafkaclient.ConsumedMessage) (string, bool) { return "evt-1", true }

	gateWithoutStore := NewGate(nil, extractor, nil)
	processed, err := gateWithoutStore.AlreadyProcessed(context.Background(), fakeMessage())
	if err != nil || processed {
		t.Fatalf("expected gate without store to pass through, got %v/%v", processed, err)
	}

	gateWithoutExtractor := NewGate(NewInMemoryStore(), nil, nil)
	processed, err = gateWithoutExtractor.AlreadyProcessed(context.Background(), fakeMessage())
	if err != nil || processed {
		t.Fatalf("expected gate without extractor to pass through, got %v/%v", processed, err)
	}
}

func TestGatePassesThroughWhenEventIDMissing(t *testing.T) {
	store := NewInMemoryStore()
	noEventID := func(message kafkaclient.ConsumedMessage) (string, bool) { return "", false }
	gate := NewGate(store, noEventID, nil)

	processed, err := gate.AlreadyProcessed(context.Background(), fakeMessage())

	if err != nil || processed {
		t.Fatalf("expected pass-through on missing event id, got %v/%v", processed, err)
	}
}

func TestGateSkipsSeenAndPassesUnseen(t *testing.T) {
	store := NewInMemoryStore()
	if err := store.Mark(context.Background(), "evt-seen"); err != nil {
		t.Fatal(err)
	}
	extractEventIDFromKey := func(message kafkaclient.ConsumedMessage) (string, bool) {
		return string(message.Key), true
	}
	gate := NewGate(store, extractEventIDFromKey, nil)

	seenMessage := fakeMessage()
	seenMessage.Key = []byte("evt-seen")
	processed, err := gate.AlreadyProcessed(context.Background(), seenMessage)
	if err != nil {
		t.Fatal(err)
	}
	if !processed {
		t.Fatal("expected seen event to be skipped")
	}

	unseenMessage := fakeMessage()
	unseenMessage.Key = []byte("evt-unseen")
	processed, err = gate.AlreadyProcessed(context.Background(), unseenMessage)
	if err != nil {
		t.Fatal(err)
	}
	if processed {
		t.Fatal("expected unseen event to pass through")
	}
}

func TestGatePropagatesStoreErrors(t *testing.T) {
	errStoreDown := errors.New("store down")
	extractor := func(message kafkaclient.ConsumedMessage) (string, bool) { return "evt-1", true }
	gate := NewGate(failingStore{err: errStoreDown}, extractor, nil)

	_, err := gate.AlreadyProcessed(context.Background(), fakeMessage())

	if !errors.Is(err, errStoreDown) {
		t.Fatalf("expected store error to propagate, got %v", err)
	}
}

type failingStore struct {
	err error
}

func (s failingStore) Seen(ctx context.Context, eventID string) (bool, error) {
	return false, s.err
}

func (s failingStore) Mark(ctx context.Context, eventID string, options ...MarkOption) error {
	return s.err
}

func TestPostgresStoreSeenQueriesByGroupAndEventID(t *testing.T) {
	querier := &fakePostgresQuerier{rowScanError: pgx.ErrNoRows}
	store := NewPostgresStore(querier, "read-service")

	seen, err := store.Seen(context.Background(), "evt-1")

	if err != nil {
		t.Fatal(err)
	}
	if seen {
		t.Fatal("expected unseen on no rows")
	}
	expectedQuery := "SELECT 1 FROM kafka_consumed_events WHERE consumer_group = $1 AND event_id = $2"
	if querier.lastQuery != expectedQuery {
		t.Fatalf("unexpected query: %q", querier.lastQuery)
	}
	if querier.lastArgs[0] != "read-service" || querier.lastArgs[1] != "evt-1" {
		t.Fatalf("unexpected args: %v", querier.lastArgs)
	}
}

func TestPostgresStoreMarkInsertsWithConflictIgnore(t *testing.T) {
	querier := &fakePostgresQuerier{}
	store := NewPostgresStore(querier, "read-service", WithTable("custom_events"))
	consumedAt := time.Date(2026, 1, 1, 0, 0, 0, 0, time.UTC)

	err := store.Mark(context.Background(), "evt-1", WithMarkConsumedAt(consumedAt))

	if err != nil {
		t.Fatal(err)
	}
	expectedStatement := "INSERT INTO custom_events (consumer_group, event_id, consumed_at) " +
		"VALUES ($1, $2, $3) ON CONFLICT DO NOTHING"
	if querier.lastExec != expectedStatement {
		t.Fatalf("unexpected statement: %q", querier.lastExec)
	}
	if querier.lastExecArgs[2] != consumedAt {
		t.Fatalf("expected consumed_at %v, got %v", consumedAt, querier.lastExecArgs[2])
	}
}

func TestPostgresStoreMarkUsesProvidedExecutor(t *testing.T) {
	querier := &fakePostgresQuerier{}
	transactionExecutor := &fakePostgresQuerier{}
	store := NewPostgresStore(querier, "read-service")

	err := store.Mark(context.Background(), "evt-1", WithMarkExecutor(transactionExecutor))

	if err != nil {
		t.Fatal(err)
	}
	if querier.lastExec != "" {
		t.Fatal("expected pool executor to be bypassed")
	}
	if transactionExecutor.lastExec == "" {
		t.Fatal("expected provided executor to receive the insert")
	}
}

type fakePostgresQuerier struct {
	lastQuery    string
	lastArgs     []any
	rowScanError error

	lastExec     string
	lastExecArgs []any
	execError    error
}

func (f *fakePostgresQuerier) Exec(
	ctx context.Context,
	sql string,
	arguments ...any,
) (pgconn.CommandTag, error) {
	f.lastExec = sql
	f.lastExecArgs = arguments
	return pgconn.CommandTag{}, f.execError
}

func (f *fakePostgresQuerier) QueryRow(ctx context.Context, sql string, args ...any) pgx.Row {
	f.lastQuery = sql
	f.lastArgs = args
	return fakeRow{scanError: f.rowScanError}
}

type fakeRow struct {
	scanError error
}

func (r fakeRow) Scan(dest ...any) error {
	if r.scanError != nil {
		return r.scanError
	}
	for _, target := range dest {
		if intTarget, ok := target.(*int); ok {
			*intTarget = 1
		}
	}
	return nil
}

func TestPostgresStoreSeenReturnsTrueWhenRowExists(t *testing.T) {
	querier := &fakePostgresQuerier{}
	store := NewPostgresStore(querier, "read-service")

	seen, err := store.Seen(context.Background(), "evt-1")

	if err != nil {
		t.Fatal(err)
	}
	if !seen {
		t.Fatal("expected seen when a row matches")
	}
}

func TestPostgresStoreSeenPropagatesQueryErrors(t *testing.T) {
	errConnectionLost := errors.New("connection lost")
	querier := &fakePostgresQuerier{rowScanError: errConnectionLost}
	store := NewPostgresStore(querier, "read-service")

	_, err := store.Seen(context.Background(), "evt-1")

	if !errors.Is(err, errConnectionLost) {
		t.Fatalf("expected query error to propagate, got %v", err)
	}
}

func TestPostgresStoreMarkPropagatesExecErrors(t *testing.T) {
	errConnectionLost := errors.New("connection lost")
	querier := &fakePostgresQuerier{execError: errConnectionLost}
	store := NewPostgresStore(querier, "read-service")

	err := store.Mark(context.Background(), "evt-1")

	if !errors.Is(err, errConnectionLost) {
		t.Fatalf("expected exec error to propagate, got %v", err)
	}
}

func TestPostgresStoreMarkDefaultsConsumedAtToNow(t *testing.T) {
	querier := &fakePostgresQuerier{}
	store := NewPostgresStore(querier, "read-service")
	before := time.Now().UTC()

	if err := store.Mark(context.Background(), "evt-1"); err != nil {
		t.Fatal(err)
	}

	after := time.Now().UTC()
	consumedAt, ok := querier.lastExecArgs[2].(time.Time)
	if !ok {
		t.Fatalf("expected time.Time consumed_at, got %T", querier.lastExecArgs[2])
	}
	if consumedAt.Before(before) || consumedAt.After(after) {
		t.Fatalf("expected now-ish consumed_at, got %v", consumedAt)
	}
}

func TestInMemoryStoreIsSafeForConcurrentUse(t *testing.T) {
	store := NewInMemoryStore()
	var group sync.WaitGroup

	for workerNumber := range 8 {
		group.Add(1)
		go func() {
			defer group.Done()
			for i := range 100 {
				eventID := fmt.Sprintf("evt-%d-%d", workerNumber, i)
				if err := store.Mark(context.Background(), eventID); err != nil {
					t.Error(err)
					return
				}
				seen, err := store.Seen(context.Background(), eventID)
				if err != nil {
					t.Error(err)
					return
				}
				if !seen {
					t.Errorf("expected %s to be seen after mark", eventID)
					return
				}
			}
		}()
	}
	group.Wait()
}
