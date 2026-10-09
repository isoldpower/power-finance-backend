package presentation

type ConnectionPresentation interface {
	OpenStream() error
	ClientGoneChannel() <-chan struct{}
	SendMessageOverConnection(message []byte) error
}

type PresenterDefinition interface {
	InitialiseRoutes() error
}
