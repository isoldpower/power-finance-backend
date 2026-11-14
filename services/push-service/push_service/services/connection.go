package services

import (
	"context"
	"log/slog"

	"github.com/power-finance/observability-go/sandbox"

	"services/push-service/internal/metrics"
	"services/push-service/push_service/types"
)

const clientEventBufferSize = 16

type DeliveryReporting int

const (
	SilentDeliveries DeliveryReporting = iota
	ReportedDeliveries
)

type PoolClient struct {
	audience      types.StreamAudience
	eventsChannel chan types.OutboxEvent
	cancel        func()
}

// Events returns read-only processed events channel.
func (pc *PoolClient) Events() <-chan types.OutboxEvent {
	return pc.eventsChannel
}

// Cancel blocks receiving SSE notifications from the server.
func (pc *PoolClient) Cancel() {
	pc.cancel()
}

type ClientsPoolService struct {
	clientsByUser  map[string]map[*PoolClient]struct{}
	registerChan   chan *PoolClient
	unregisterChan chan *PoolClient
	doneChannel    chan struct{}
	reporting      DeliveryReporting
}

func NewClientsPoolService(reporting DeliveryReporting) *ClientsPoolService {
	return &ClientsPoolService{
		clientsByUser:  make(map[string]map[*PoolClient]struct{}),
		registerChan:   make(chan *PoolClient),
		unregisterChan: make(chan *PoolClient),
		doneChannel:    make(chan struct{}),
		reporting:      reporting,
	}
}

// FanoutEvents provides a way to specify a sink channel that will be used
// to fanout all the events processed by pool. It runs until the sink channel
// closes or ctx is cancelled, detaching every client on exit.
func (cps *ClientsPoolService) FanoutEvents(ctx context.Context, eventsChannel <-chan types.OutboxEvent) {
	defer close(cps.doneChannel)

	for {
		select {
		case <-ctx.Done():
			cps.removeAllClients()
			return
		case client := <-cps.registerChan:
			cps.addClient(client)
		case client := <-cps.unregisterChan:
			cps.removeClient(client)
		case event, isOpen := <-eventsChannel:
			if !isOpen {
				cps.removeAllClients()
				return
			}
			cps.dispatch(event)
		}
	}
}

// Subscribe creates new pool-oriented connection that will consume events from this pool.
func (cps *ClientsPoolService) Subscribe(audience types.StreamAudience) (types.ClientSubscription, bool) {
	client := &PoolClient{
		audience:      audience,
		eventsChannel: make(chan types.OutboxEvent, clientEventBufferSize),
	}
	client.cancel = func() { cps.unregister(client) }

	select {
	case cps.registerChan <- client:
		return client, true
	case <-cps.doneChannel:
		return nil, false
	}
}

func (cps *ClientsPoolService) unregister(client *PoolClient) {
	select {
	case cps.unregisterChan <- client:
	case <-cps.doneChannel:
	}
}

func (cps *ClientsPoolService) dispatch(event types.OutboxEvent) {
	deliveredConnectionCount := 0
	for _, client := range cps.candidateClients(event) {
		if client.audience.SandboxID != event.SandboxID {
			continue
		}
		if cps.deliver(client, event) {
			deliveredConnectionCount++
		}
	}

	cps.reportDelivery(event, deliveredConnectionCount)
}

func (cps *ClientsPoolService) candidateClients(event types.OutboxEvent) []*PoolClient {
	candidates := make([]*PoolClient, 0)
	if event.UserID == types.GlobalPartitionKey {
		for _, userClients := range cps.clientsByUser {
			for client := range userClients {
				candidates = append(candidates, client)
			}
		}
		return candidates
	}

	for client := range cps.clientsByUser[event.UserID] {
		candidates = append(candidates, client)
	}
	return candidates
}

func (cps *ClientsPoolService) deliver(client *PoolClient, event types.OutboxEvent) bool {
	select {
	case client.eventsChannel <- event:
		return true
	default:
		metrics.EventDroppedSlowClient()
		slog.WarnContext(
			eventLogContext(event),
			"dropping event for slow client",
			"user_id", client.audience.ExternalUserID,
			"event_id", event.EventID,
			"event_type", event.EventType,
		)
		return false
	}
}

func (cps *ClientsPoolService) reportDelivery(event types.OutboxEvent, deliveredConnectionCount int) {
	if cps.reporting != ReportedDeliveries {
		return
	}

	if deliveredConnectionCount == 0 {
		slog.InfoContext(
			eventLogContext(event),
			"event skipped, no stream connection matches its user and sandbox",
			"user_id", event.UserID,
			"event_id", event.EventID,
			"event_type", event.EventType,
		)
		return
	}

	slog.InfoContext(
		eventLogContext(event),
		"event delivered",
		"user_id", event.UserID,
		"event_id", event.EventID,
		"event_type", event.EventType,
		"connections", deliveredConnectionCount,
	)
}

func eventLogContext(event types.OutboxEvent) context.Context {
	if event.SandboxID == "" {
		return context.Background()
	}

	return sandbox.AttachID(context.Background(), event.SandboxID)
}

func (cps *ClientsPoolService) addClient(client *PoolClient) {
	userClients, known := cps.clientsByUser[client.audience.ExternalUserID]
	if !known {
		userClients = make(map[*PoolClient]struct{})
		cps.clientsByUser[client.audience.ExternalUserID] = userClients
	}

	userClients[client] = struct{}{}
	metrics.SubscriberAdded()
}

func (cps *ClientsPoolService) removeClient(client *PoolClient) {
	userClients, knownClient := cps.clientsByUser[client.audience.ExternalUserID]
	if !knownClient {
		return
	}
	if _, ok := userClients[client]; !ok {
		return
	}

	delete(userClients, client)
	if len(userClients) == 0 {
		delete(cps.clientsByUser, client.audience.ExternalUserID)
	}
	close(client.eventsChannel)
	metrics.SubscriberRemoved()
}

func (cps *ClientsPoolService) removeAllClients() {
	for userID, userClients := range cps.clientsByUser {
		for client := range userClients {
			close(client.eventsChannel)
		}
		delete(cps.clientsByUser, userID)
	}
	metrics.SubscribersReset()
}
