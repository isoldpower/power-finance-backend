package utilities

type CancelFunc func()
type SlavesSlice []<-chan struct{}
type MasterChannel chan<- struct{}

// DuplicateHeadlessDoneSignal is a utility function which purpose is to replicate master's
// channel signal across all its slaves. It can be used to automatically populate
// done signal across multiple consumers.
// First returned value is a master channel.
// Second is a slice containing of slave channels.
// Last argument is a cancellation function used to stop waiting on master channel.
func DuplicateHeadlessDoneSignal(amount int) (MasterChannel, SlavesSlice, CancelFunc) {
	cancelChannel := make(chan struct{})
	masterSignalChannel := make(chan struct{})
	slaveSignals := make([]chan struct{}, amount)
	for i := range slaveSignals {
		slaveSignals[i] = make(chan struct{}, 1)
	}

	go func() {
		select {
		case <-cancelChannel:
			return
		case <-masterSignalChannel:
			for _, slave := range slaveSignals {
				slave <- struct{}{}
			}
		}
	}()

	abortWaiting := func() { cancelChannel <- struct{}{} }
	readOnlySlaves := BlockChannelsWrite(slaveSignals)

	return masterSignalChannel, readOnlySlaves, abortWaiting
}

// DuplicateDoneSignal is a utility function which purpose is to replicate master's
// channel signal across all its slaves. It can be used to automatically populate
// done signal across multiple consumers.
// First returned value is a master channel.
// Second is a slice containing of slave channels.
// Last argument is a cancellation function used to stop waiting on master channel.
func DuplicateDoneSignal(
	masterChannel <-chan struct{},
	amount int,
) (SlavesSlice, CancelFunc) {
	cancelChannel := make(chan struct{})
	slaveSignals := make([]chan struct{}, amount)
	for i := range slaveSignals {
		slaveSignals[i] = make(chan struct{}, 1)
	}

	go func() {
		select {
		case <-cancelChannel:
			return
		case <-masterChannel:
			for _, slave := range slaveSignals {
				slave <- struct{}{}
			}
		}
	}()

	abortWaiting := func() {
		cancelChannel <- struct{}{}
	}
	readOnlySlaves := BlockChannelsWrite(slaveSignals)

	return readOnlySlaves, abortWaiting
}
