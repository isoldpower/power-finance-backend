package kafka

const clientID = "webhook-service"

// Config names the brokers, the topics consumed and the topics produced to.
type Config struct {
	BootstrapServers          string
	OutboxTopics              []string
	GroupID                   string
	RetryTopic                string
	DLQTopic                  string
	NotificationsInboundTopic string
}
