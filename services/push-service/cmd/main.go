package main

import (
	"services/push-service/push_service"
)

//TODO:
// 1) Implement server with connections pooling
// 2) Implement Kafka listener
// 3) Implement Go version of Python Kafka consumer library to support DLQ and more
// 4) Implement messages projection using step 3

func main() {
	push_service.StartPushService()
}
