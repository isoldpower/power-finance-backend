package postgres

import (
	"context"

	"github.com/power-finance/kafka-client-go/consumer/dedupe"
)

type Stores struct {
	ConfigStore   *ConfigStore
	DeliveryStore *DeliveryStore
	DedupeStore   *dedupe.PostgresStore
}

// Bootstrap opens the pool, applies the schema and builds the stores; the
// returned cleanup closes the pool and must be called on shutdown.
func Bootstrap(
	rootContext context.Context,
	config Config,
	dedupeGroup string,
) (stores *Stores, cleanup func(), err error) {
	postgresPool, poolErr := Connect(rootContext, config.DSN)
	if poolErr != nil {
		return nil, nil, poolErr
	}

	if schemaErr := EnsureSchema(rootContext, postgresPool); schemaErr != nil {
		postgresPool.Close()
		return nil, nil, schemaErr
	}

	return &Stores{
		ConfigStore:   NewConfigStore(postgresPool),
		DeliveryStore: NewDeliveryStore(postgresPool),
		DedupeStore:   dedupe.NewPostgresStore(postgresPool, dedupeGroup),
	}, postgresPool.Close, nil
}
