package services

import (
	"log/slog"

	"services/push-service/push_service/types"
)

const clientEventBufferSize = 16

type PoolClient struct {
	externalUserID string
	eventsChannel  chan types.OutboxEvent
	cancel         func()
}

func (pc *PoolClient) Events() <-chan types.OutboxEvent {
	return pc.eventsChannel
}

func (pc *PoolClient) Cancel() {
	pc.cancel()
}

type ClientsPoolService struct {
	clientsByUser  map[string]map[*PoolClient]struct{}
	registerChan   chan *PoolClient
	unregisterChan chan *PoolClient
	doneChannel    chan struct{}
}

func NewClientsPoolService() *ClientsPoolService {
	return &ClientsPoolService{
		clientsByUser:  make(map[string]map[*PoolClient]struct{}),
		registerChan:   make(chan *PoolClient),
		unregisterChan: make(chan *PoolClient),
		doneChannel:    make(chan struct{}),
	}
}

func (cps *ClientsPoolService) FanoutEvents(eventsChannel <-chan types.OutboxEvent) {
	defer close(cps.doneChannel)

	for {
		select {
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

func (cps *ClientsPoolService) Subscribe(externalUserID string) (types.ClientSubscription, bool) {
	client := &PoolClient{
		externalUserID: externalUserID,
		eventsChannel:  make(chan types.OutboxEvent, clientEventBufferSize),
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
	if event.UserID == types.GlobalPartitionKey {
		for _, userClients := range cps.clientsByUser {
			for client := range userClients {
				cps.deliver(client, event)
			}
		}
		return
	}

	for client := range cps.clientsByUser[event.UserID] {
		cps.deliver(client, event)
	}
}

func (cps *ClientsPoolService) deliver(client *PoolClient, event types.OutboxEvent) {
	select {
	case client.eventsChannel <- event:
	default:
		slog.Warn(
			"dropping event for slow client",
			"user_id", client.externalUserID,
			"event_id", event.EventID,
			"event_type", event.EventType,
		)
	}
}

func (cps *ClientsPoolService) addClient(client *PoolClient) {
	userClients, known := cps.clientsByUser[client.externalUserID]
	if !known {
		userClients = make(map[*PoolClient]struct{})
		cps.clientsByUser[client.externalUserID] = userClients
	}

	userClients[client] = struct{}{}
}

func (cps *ClientsPoolService) removeClient(client *PoolClient) {
	userClients, known := cps.clientsByUser[client.externalUserID]
	if !known {
		return
	}
	if _, ok := userClients[client]; !ok {
		return
	}

	delete(userClients, client)
	if len(userClients) == 0 {
		delete(cps.clientsByUser, client.externalUserID)
	}
	close(client.eventsChannel)
}

func (cps *ClientsPoolService) removeAllClients() {
	for userID, userClients := range cps.clientsByUser {
		for client := range userClients {
			close(client.eventsChannel)
		}
		delete(cps.clientsByUser, userID)
	}
}
