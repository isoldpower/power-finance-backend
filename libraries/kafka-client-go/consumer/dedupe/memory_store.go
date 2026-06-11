package dedupe

import (
	"context"
	"sync"
)

type InMemoryStore struct {
	mu           sync.Mutex
	seenEventIDs map[string]struct{}
}

func NewInMemoryStore() *InMemoryStore {
	return &InMemoryStore{seenEventIDs: make(map[string]struct{})}
}

func (s *InMemoryStore) Seen(ctx context.Context, eventID string) (bool, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	_, seen := s.seenEventIDs[eventID]

	return seen, nil
}

func (s *InMemoryStore) Mark(
	ctx context.Context,
	eventID string,
	options ...MarkOption,
) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.seenEventIDs[eventID] = struct{}{}

	return nil
}
