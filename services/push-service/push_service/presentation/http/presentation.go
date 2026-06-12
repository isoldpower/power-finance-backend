package http

import (
	"net/http"
	"services/push-service/internal/log"
	"services/push-service/push_service/handlers"
	"services/push-service/push_service/presentation"
)

type HttpPresentation struct {
	notificationsHandler *handlers.SSENotificationsHandler
}

func NewHttpPresentation(
	notificationsHandler *handlers.SSENotificationsHandler,
) *HttpPresentation {
	return &HttpPresentation{
		notificationsHandler: notificationsHandler,
	}
}

func (hp *HttpPresentation) HandleGetNotifications(
	writer http.ResponseWriter,
	request *http.Request,
) {
	externalUserID, authenticated := handlers.AuthenticatedUserID(request)
	if !authenticated {
		http.Error(writer, "Authenticated user is required", http.StatusUnauthorized)
		return
	}

	httpConnection := NewSseHttpConnection(writer, request)
	goneChannel := httpConnection.ClientGoneChannel()

	eventsChannel, unsubscribe, subscribed := hp.notificationsHandler.Subscribe(externalUserID)
	if subscribed {
		defer unsubscribe()
		responseChannel := make(chan []byte)

		go hp.consumeResponseMessages(httpConnection, responseChannel)
		hp.notificationsHandler.SpinUntilDone(goneChannel, eventsChannel, responseChannel)

		close(responseChannel)
	}
}

func (hp *HttpPresentation) consumeResponseMessages(
	httpConnection presentation.ConnectionPresentation,
	responseChannel chan []byte,
) {
	for buffer := range responseChannel {
		transportErr := httpConnection.SendMessageOverConnection(buffer)
		if transportErr != nil {
			log.PrintError("Failed to send the Kafka event to the connection consumer", transportErr)
		} else {
			log.Successln("Successfully sent the Kafka event to the connection consumer")
		}
	}
}
