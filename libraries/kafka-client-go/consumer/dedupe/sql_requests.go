package dedupe

import "fmt"

const defaultTable = "kafka_consumed_events"

const CreateTableSQL = `
CREATE TABLE IF NOT EXISTS kafka_consumed_events (
    consumer_group TEXT NOT NULL,
    event_id       TEXT NOT NULL,
    consumed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (consumer_group, event_id)
);

CREATE INDEX IF NOT EXISTS kafka_consumed_events_consumed_at_idx
    ON kafka_consumed_events (consumed_at);
`

func getSelectSeenEventTemplateSQL(table string) string {
	return fmt.Sprintf(
		"SELECT 1 FROM %s WHERE consumer_group = $1 AND event_id = $2",
		table,
	)
}

func getInsertConsumedEventTemplateSQL(table string) string {
	return fmt.Sprintf(
		"INSERT INTO %s (consumer_group, event_id, consumed_at) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
		table,
	)
}
