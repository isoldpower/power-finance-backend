package services

const GlobalPartitionKey = "GLOBAL"

type OutboxEvent struct {
	EventID       string
	EventType     string
	AggregateType string
	UserID        string
	Payload       []byte
}

func (event OutboxEvent) IsAddressedTo(externalUserID string) bool {
	return event.UserID == externalUserID || event.UserID == GlobalPartitionKey
}
