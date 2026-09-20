package propagation

import "github.com/power-finance/kafka-client-go/headers"

type KafkaHeaderCarrier struct {
	kafkaHeaders headers.KafkaHeaders
}

func NewKafkaHeaderCarrier(kafkaHeaders headers.KafkaHeaders) KafkaHeaderCarrier {
	return KafkaHeaderCarrier{kafkaHeaders: kafkaHeaders}
}

func (c KafkaHeaderCarrier) Get(key string) string {
	value, isFound := headers.Get(c.kafkaHeaders, key)
	if !isFound {
		return ""
	}

	return value
}

func (c KafkaHeaderCarrier) Set(key string, value string) {
	c.kafkaHeaders = headers.Merge(
		c.kafkaHeaders,
		headers.String(key, value),
	)
}

func (c KafkaHeaderCarrier) Keys() []string {
	keys := make([]string, 0, len(c.kafkaHeaders))
	for _, header := range c.kafkaHeaders {
		keys = append(keys, header.Key)
	}

	return keys
}
