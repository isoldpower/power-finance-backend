package main

import (
	"services/push-service/push_service"
)

//TODO:
// 1) Implement messages projection: decode proto envelopes in
//    EventsProjectionService.translateKafkaMessage and fan out typed events

func main() {
	push_service.StartPushService()
}
