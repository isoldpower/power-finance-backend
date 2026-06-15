package kafka

const clientID = "webhook-service"

type Config struct {
	BootstrapServers          string
	OutboxTopics              []string
	GroupID                   string
	RetryTopic                string
	DLQTopic                  string
	NotificationsInboundTopic string
}
