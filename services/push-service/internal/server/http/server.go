package http

import (
	"context"
	"errors"
	"fmt"
	"net"
	"net/http"
	"os/signal"
	"services/push-service/internal/color"
	"services/push-service/internal/log"
	"services/push-service/internal/server"
	"services/push-service/internal/signals"
	"services/push-service/internal/utilities"
	"sync"
	"syscall"
	"time"
)

type HTTPServer struct {
	basicConfig EstablishedHTTPProcessConfig
	router      *http.ServeMux
	listener    net.Listener
	server      *http.Server

	doneChannel             chan error
	gracefulShutdownChannel chan bool
	cancelRequests          context.CancelFunc
}

func NewHTTPServer(basicConfig EstablishedHTTPProcessConfig) (*HTTPServer, error) {
	serveAddress := fmt.Sprintf("%s:%d", basicConfig.Host, basicConfig.Port)
	listener, listenerErr := createListener(serveAddress, basicConfig.NetworkType)
	if listenerErr != nil {
		log.PrintError("Failed to create HTTP listener", listenerErr)
		return nil, listenerErr
	}

	router := http.NewServeMux()
	baseContext, cancelRequests := context.WithCancel(context.Background())

	return &HTTPServer{
		basicConfig: basicConfig,
		router:      router,
		listener:    listener,
		server: &http.Server{
			Addr:    serveAddress,
			Handler: router,
			BaseContext: func(net.Listener) context.Context {
				return baseContext
			},
		},
		doneChannel:             make(chan error, 1),
		gracefulShutdownChannel: make(chan bool, 1),
		cancelRequests:          cancelRequests,
	}, nil
}

func (hs *HTTPServer) Run(config server.ProcessBootstrapConfig) {
	keyboardShutdown := signals.NewKeyboardSignalHandler(hs.stopServerFromKeyboard)

	waitGroup := sync.WaitGroup{}
	waitGroup.Go(func() {
		hs.serveRouter()
	})

	signals.TrackSignalSafe(keyboardShutdown, hs.gracefulShutdownChannel)
	waitGroup.Wait()
}

func (hs *HTTPServer) Shutdown() server.ShutdownRoutine {
	shutdownTimestamp := time.Now()
	enforceShutdown := make(chan struct{}, 1)

	return server.ShutdownRoutine{
		StartedAt: shutdownTimestamp,
		ForceStop: func(message string) error {
			log.Warnln("%s server shutdown enforced through code: %s", color.Blue("HTTP"), message)

			enforceShutdown <- struct{}{}
			return nil
		},
	}
}

func (hs *HTTPServer) RegisterMiddleware(middleware *RouteMiddleware) {
	hs.basicConfig.Middlewares = sortMiddlewares(
		append(hs.basicConfig.Middlewares, middleware),
	)
}

func (hs *HTTPServer) AddRoute(
	pattern string,
	handler func(http.ResponseWriter, *http.Request),
) {
	handlerWithMiddleware := func(writer http.ResponseWriter, request *http.Request) {
		for _, middleware := range hs.basicConfig.Middlewares {
			requestAfterMiddleware, shouldContinue := middleware.ServeHTTP(writer, request)
			if !shouldContinue {
				return
			}

			request = requestAfterMiddleware
		}

		handler(writer, request)
	}

	hs.router.HandleFunc(pattern, handlerWithMiddleware)
}

func (hs *HTTPServer) GetDoneChannel() <-chan error {
	return hs.doneChannel
}

func (hs *HTTPServer) serveRouter() {
	serveErr := hs.server.Serve(hs.listener)
	if serveErr != nil && !errors.Is(serveErr, http.ErrServerClosed) {
		log.PrintError("Error occurred while serving HTTP listener", serveErr)
	}
}

func (hs *HTTPServer) stopServerFromKeyboard(ctx context.Context) error {
	log.Processln("Shutting down %s server gracefully", color.Blue("HTTP"))
	log.RaiseLog(func() {
		log.Debugln("%s Interrupted by %s context", log.GetIcon(log.GearIcon), ctx)
	})

	forceShutdown, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()
	hs.shutdownWithContextAndTimeout(forceShutdown)

	return nil
}

func (hs *HTTPServer) shutdownWithChannelAndTimeout(forceShutdownChannel <-chan struct{}) {
	timeoutContext, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	channelContext, cancel2 := utilities.ChannelToContext(timeoutContext, forceShutdownChannel)
	defer cancel()
	defer cancel2()

	hs.shutdownWithContext(channelContext)
}

func (hs *HTTPServer) shutdownWithContextAndTimeout(passedContext context.Context) {
	timeoutContext, cancel := context.WithTimeout(passedContext, 5*time.Second)
	defer cancel()

	hs.shutdownWithContext(timeoutContext)
}

func (hs *HTTPServer) shutdownWithContext(cancelContext context.Context) {
	hs.gracefulShutdownChannel <- true
	hs.cancelRequests()
	if shutdownErr := hs.server.Shutdown(cancelContext); shutdownErr != nil {
		log.PrintError("Server forced to shutdown with error", shutdownErr)
		hs.doneChannel <- shutdownErr
	} else {
		hs.doneChannel <- nil
	}
}
