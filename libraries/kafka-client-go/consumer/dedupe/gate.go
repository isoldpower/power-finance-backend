package dedupe

import (
	"context"
	"log/slog"

	kafkaclient "github.com/power-finance/kafka-client-go"
)

type EventIDExtractor func(message kafkaclient.ConsumedMessage) (eventID string, found bool)

type Gate struct {
	store     Store
	extractor EventIDExtractor
	logger    *slog.Logger
}

func NewGate(store Store, extractor EventIDExtractor, logger *slog.Logger) *Gate {
	if logger == nil {
		logger = slog.Default()
	}

	storeConfigured := store != nil
	extractorConfigured := extractor != nil
	if storeConfigured != extractorConfigured {
		logger.Warn(
			"kafka.dedupe.disabled_partial_config",
			slog.Bool("store_configured", storeConfigured),
			slog.Bool("extractor_configured", extractorConfigured),
		)
	}

	return &Gate{
		store:     store,
		extractor: extractor,
		logger:    logger,
	}
}

func (g *Gate) AlreadyProcessed(
	ctx context.Context,
	message kafkaclient.ConsumedMessage,
) (bool, error) {
	if g.store == nil || g.extractor == nil {
		return false, nil
	}

	eventID, isFound := g.extractor(message)
	if !isFound || eventID == "" {
		return false, nil
	}

	isSeen, seenErr := g.store.Seen(ctx, eventID)
	if seenErr != nil {
		return false, seenErr
	}

	if isSeen {
		g.logger.DebugContext(ctx, "kafka.dedupe.skip", slog.String("event_id", eventID))
		return true, nil
	} else {
		return false, nil
	}
}

// MarkProcessed records the message's event id as consumed so a redelivery is
// skipped by AlreadyProcessed; a no-op without a store/extractor or event id.
func (g *Gate) MarkProcessed(
	ctx context.Context,
	message kafkaclient.ConsumedMessage,
) error {
	if g.store == nil || g.extractor == nil {
		return nil
	}

	eventID, isFound := g.extractor(message)
	if !isFound || eventID == "" {
		return nil
	}

	return g.store.Mark(ctx, eventID)
}
