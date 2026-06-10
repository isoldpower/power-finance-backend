package utilities

func BlockChannelsWrite[T struct{}](origin []chan T) []<-chan T {
	readOnlyOrigin := make([]<-chan T, 0, len(origin))
	for _, channel := range origin {
		readOnlyOrigin = append(readOnlyOrigin, channel)
	}

	return readOnlyOrigin
}

func BlockChannelsRead[T struct{}](origin []chan T) []chan<- T {
	readOnlyOrigin := make([]chan<- T, 0, len(origin))
	for _, channel := range origin {
		readOnlyOrigin = append(readOnlyOrigin, channel)
	}

	return readOnlyOrigin
}
