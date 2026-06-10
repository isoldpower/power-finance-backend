package push_service

type BasicHandler[T struct{}] interface {
	HandleRequest(T)
}
