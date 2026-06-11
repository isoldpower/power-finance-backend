package dedupe

import "context"

type Store interface {
	Seen(ctx context.Context, eventID string) (bool, error)
	Mark(ctx context.Context, eventID string, options ...MarkOption) error
}
