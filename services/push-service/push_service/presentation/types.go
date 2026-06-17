package presentation

type ConnectionPresentation interface {
	ClientGoneChannel() <-chan struct{}
	SendMessageOverConnection(message []byte) error
}

type PresenterDefinition interface {
	InitialiseRoutes() error
}
