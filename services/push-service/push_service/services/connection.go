package services

import (
	"services/push-service/internal/log"
)

const clientEventBufferSize = 16

type PoolClient struct {
	externalUserID string
	eventsChannel  chan OutboxEvent
}

func (pc *PoolClient) Events() <-chan OutboxEvent {
	return pc.eventsChannel
}

type ClientsPoolService struct {
	clients        map[*PoolClient]struct{}
	registerChan   chan *PoolClient
	unregisterChan chan *PoolClient
	doneChannel    chan struct{}
}

func NewClientsPoolService() *ClientsPoolService {
	return &ClientsPoolService{
		clients:        make(map[*PoolClient]struct{}),
		registerChan:   make(chan *PoolClient),
		unregisterChan: make(chan *PoolClient),
		doneChannel:    make(chan struct{}),
	}
}

func (cps *ClientsPoolService) FanoutEvents(eventsChannel <-chan OutboxEvent) {
	defer close(cps.doneChannel)

	for {
		select {
		case client := <-cps.registerChan:
			cps.clients[client] = struct{}{}
		case client := <-cps.unregisterChan:
			cps.removeClient(client)
		case event, isOpen := <-eventsChannel:
			if !isOpen {
				cps.removeAllClients()
				return
			}
			cps.broadcast(event)
		}
	}
}

func (cps *ClientsPoolService) Register(externalUserID string) (*PoolClient, bool) {
	client := &PoolClient{
		externalUserID: externalUserID,
		eventsChannel:  make(chan OutboxEvent, clientEventBufferSize),
	}
	select {
	case cps.registerChan <- client:
		return client, true
	case <-cps.doneChannel:
		return nil, false
	}
}

func (cps *ClientsPoolService) Unregister(client *PoolClient) {
	select {
	case cps.unregisterChan <- client:
	case <-cps.doneChannel:
	}
}

func (cps *ClientsPoolService) broadcast(event OutboxEvent) {
	for client := range cps.clients {
		if !event.IsAddressedTo(client.externalUserID) {
			continue
		}

		select {
		case client.eventsChannel <- event:
		default:
			log.Warnln("Dropping event for a slow client")
		}
	}
}

func (cps *ClientsPoolService) removeClient(client *PoolClient) {
	if _, ok := cps.clients[client]; ok {
		delete(cps.clients, client)
		close(client.eventsChannel)
	}
}

func (cps *ClientsPoolService) removeAllClients() {
	for client := range cps.clients {
		delete(cps.clients, client)
		close(client.eventsChannel)
	}
}
