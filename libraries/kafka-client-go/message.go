package kafkaclient

import "github.com/power-finance/kafka-client-go/headers"

type ConsumedMessage struct {
	Topic     string
	Partition int32
	Offset    int64
	Key       []byte
	Value     []byte
	Headers   headers.KafkaHeaders
}
