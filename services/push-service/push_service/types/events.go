package types

const GlobalPartitionKey = "GLOBAL"

type OutboxEvent struct {
	EventID       string
	EventType     string
	AggregateType string
	UserID        string
	Payload       []byte
}
