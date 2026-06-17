package publisher

import (
	"context"
	"errors"
	"sync"
	"time"

	"github.com/power-finance/kafka-client-go/headers"
	"github.com/power-finance/kafka-client-go/publisher/acknowledgement"
	"github.com/power-finance/kafka-client-go/publisher/compression"
	"github.com/twmb/franz-go/pkg/kgo"
)

type MessagePublisher interface {
	Publish(
		ctx context.Context,
		topic string,
		key []byte,
		value []byte,
		kafkaHeaders headers.KafkaHeaders,
	) error
}

type ProducerConfig struct {
	BootstrapServers  string
	ClientID          string
	Acknowledgement   acknowledgement.AcknowledgementMode
	EnableIdempotence bool
	Linger            time.Duration
	Compression       compression.CompressionType
}

func DefaultProducerConfig(bootstrapServers string) ProducerConfig {
	return ProducerConfig{
		BootstrapServers:  bootstrapServers,
		Acknowledgement:   acknowledgement.AcknowledgeAllInSyncReplicas,
		EnableIdempotence: true,
		Linger:            5 * time.Millisecond,
		Compression:       compression.CompressionGzip,
	}
}

type KafkaPublisher struct {
	config ProducerConfig
	mutex  sync.Mutex
	client *kgo.Client
}

func NewKafkaPublisher(config ProducerConfig) *KafkaPublisher {
	return &KafkaPublisher{config: config}
}

func (p *KafkaPublisher) Start(ctx context.Context) error {
	p.mutex.Lock()
	defer p.mutex.Unlock()
	if p.client != nil {
		return nil
	}

	clientOptions, optionsErr := buildClientOptions(p.config)
	if optionsErr != nil {
		return optionsErr
	}

	client, clientErr := kgo.NewClient(clientOptions...)
	if clientErr != nil {
		return clientErr
	}

	if pingErr := client.Ping(ctx); pingErr != nil {
		client.Close()

		return pingErr
	}

	p.client = client
	return nil
}

func (p *KafkaPublisher) Stop() {
	p.mutex.Lock()
	defer p.mutex.Unlock()
	if p.client == nil {
		return
	}

	p.client.Close()
	p.client = nil
}

func (p *KafkaPublisher) Publish(
	ctx context.Context,
	topic string,
	key []byte,
	value []byte,
	kafkaHeaders headers.KafkaHeaders,
) error {
	p.mutex.Lock()
	client := p.client
	p.mutex.Unlock()

	if client == nil {
		return errors.New("publisher: KafkaPublisher used before Start()")
	}

	record := &kgo.Record{
		Topic:   topic,
		Key:     key,
		Value:   value,
		Headers: toRecordHeaders(kafkaHeaders),
	}

	return client.ProduceSync(ctx, record).FirstErr()
}

func toRecordHeaders(kafkaHeaders headers.KafkaHeaders) []kgo.RecordHeader {
	if len(kafkaHeaders) == 0 {
		return nil
	}

	recordHeaders := make([]kgo.RecordHeader, len(kafkaHeaders))
	for i, header := range kafkaHeaders {
		recordHeaders[i] = kgo.RecordHeader{Key: header.Key, Value: header.Value}
	}

	return recordHeaders
}
