package postgres

import (
	"context"

	"github.com/power-finance/kafka-client-go/consumer/dedupe"
)

type Stores struct {
	ConfigStore      *ConfigStore
	DeliveryStore    *DeliveryStore
	DeliveryLogStore *DeliveryLogStore
	DedupeStore      *dedupe.PostgresStore
}

// Bootstrap opens the pool and builds the stores; the returned cleanup closes
// the pool and must be called on shutdown.
func Bootstrap(
	rootContext context.Context,
	config Config,
	dedupeGroup string,
) (stores *Stores, cleanup func(), err error) {
	postgresPool, poolErr := Connect(rootContext, config.DSN)
	if poolErr != nil {
		return nil, nil, poolErr
	}

	return &Stores{
		ConfigStore:      NewConfigStore(postgresPool),
		DeliveryStore:    NewDeliveryStore(postgresPool),
		DeliveryLogStore: NewDeliveryLogStore(postgresPool),
		DedupeStore:      dedupe.NewPostgresStore(postgresPool, dedupeGroup),
	}, postgresPool.Close, nil
}
