package kafka

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/power-finance/kafka-client-go/headers"
	"github.com/power-finance/kafka-client-go/publisher"

	"services/webhook-service/webhook_service/types"
)

type notificationRequest struct {
	UserID         int            `json:"user_id"`
	UserExternalID string         `json:"user_external_id"`
	Short          string         `json:"short"`
	Message        string         `json:"message"`
	Payload        map[string]any `json:"payload,omitempty"`
}

type Producer struct {
	publisher                 *publisher.KafkaPublisher
	notificationsInboundTopic string
}

func NewProducer(bootstrapServers, notificationsInboundTopic string) *Producer {
	config := publisher.DefaultProducerConfig(bootstrapServers)
	config.ClientID = clientID

	return &Producer{
		publisher:                 publisher.NewKafkaPublisher(config),
		notificationsInboundTopic: notificationsInboundTopic,
	}
}

func (p *Producer) Start(ctx context.Context) error {
	return p.publisher.Start(ctx)
}

func (p *Producer) Stop() {
	p.publisher.Stop()
}

// RequestNotification asks the write-service to create a user-facing
// notification describing a delivery outcome.
func (p *Producer) RequestNotification(
	ctx context.Context,
	delivery types.Delivery,
	short string,
	message string,
) error {
	request := notificationRequest{
		UserID:         delivery.UserID,
		UserExternalID: delivery.UserExternalID,
		Short:          short,
		Message:        message,
		Payload: map[string]any{
			"webhook_id":  delivery.WebhookID,
			"delivery_id": delivery.ID,
			"event_type":  delivery.EventType,
		},
	}

	value, marshalErr := json.Marshal(request)
	if marshalErr != nil {
		return fmt.Errorf("kafka: marshal notification request: %w", marshalErr)
	}

	return p.publisher.Publish(
		ctx,
		p.notificationsInboundTopic,
		[]byte(delivery.UserExternalID),
		value,
		headers.KafkaHeaders{
			headers.Time(headers.FailedAt, time.Now().UTC()),
		},
	)
}
