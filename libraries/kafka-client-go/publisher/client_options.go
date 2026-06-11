package publisher

import (
	"fmt"
	"strings"

	"github.com/power-finance/kafka-client-go/publisher/acknowledgement"
	"github.com/power-finance/kafka-client-go/publisher/compression"
	"github.com/twmb/franz-go/pkg/kgo"
)

func buildClientOptions(config ProducerConfig) ([]kgo.Opt, error) {
	builder := newClientOptionsBuilder(config)

	return builder.
		withSeedBrokers().
		withClientID().
		withLinger().
		withAcknowledgement().
		withIdempotence().
		withCompression().
		build()
}

type clientOptionsBuilder struct {
	config  ProducerConfig
	options []kgo.Opt
	err     error
}

func newClientOptionsBuilder(config ProducerConfig) *clientOptionsBuilder {
	return &clientOptionsBuilder{config: config}
}

func (cob *clientOptionsBuilder) withSeedBrokers() *clientOptionsBuilder {
	brokers := strings.Split(cob.config.BootstrapServers, ",")
	cob.options = append(cob.options, kgo.SeedBrokers(brokers...))

	return cob
}

func (cob *clientOptionsBuilder) withClientID() *clientOptionsBuilder {
	if cob.config.ClientID != "" {
		cob.options = append(cob.options, kgo.ClientID(cob.config.ClientID))
	}

	return cob
}

func (cob *clientOptionsBuilder) withLinger() *clientOptionsBuilder {
	cob.options = append(cob.options, kgo.ProducerLinger(cob.config.Linger))

	return cob
}

func (cob *clientOptionsBuilder) withAcknowledgement() *clientOptionsBuilder {
	cob.options = append(
		cob.options,
		kgo.RequiredAcks(cob.acknowledgement().RequiredAcknowledgements()),
	)

	return cob
}

func (cob *clientOptionsBuilder) withIdempotence() *clientOptionsBuilder {
	if !cob.config.EnableIdempotence {
		cob.options = append(cob.options, kgo.DisableIdempotentWrite())

		return cob
	}

	if !cob.acknowledgement().SupportsIdempotence() {
		cob.err = fmt.Errorf(
			"publisher: idempotent producer is incompatible with %q acknowledgement",
			cob.acknowledgement().Name(),
		)
	}

	return cob
}

func (cob *clientOptionsBuilder) withCompression() *clientOptionsBuilder {
	cob.options = append(cob.options, kgo.ProducerBatchCompression(cob.compression().Codec()))

	return cob
}

func (cob *clientOptionsBuilder) build() ([]kgo.Opt, error) {
	if cob.err != nil {
		return nil, cob.err
	}

	return cob.options, nil
}

func (cob *clientOptionsBuilder) acknowledgement() acknowledgement.AcknowledgementMode {
	if cob.config.Acknowledgement == nil {
		return acknowledgement.AcknowledgeAllInSyncReplicas
	}

	return cob.config.Acknowledgement
}

func (cob *clientOptionsBuilder) compression() compression.CompressionType {
	if cob.config.Compression == nil {
		return compression.CompressionNone
	}

	return cob.config.Compression
}
