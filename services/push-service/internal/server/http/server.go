package http

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"net"
	"net/http"
	"os/signal"
	"services/push-service/internal/server"
	"services/push-service/internal/signals"
	"sync"
	"syscall"
	"time"
)

type HTTPServer struct {
	basicConfig EstablishedHTTPProcessConfig
	router      *http.ServeMux
	listener    net.Listener
	server      *http.Server

	gracefulShutdownChannel chan bool
	cancelRequests          context.CancelFunc
}

// NewHTTPServer creates fresh HTTP server using `basicConfig` options as a single
// source of configuration.
func NewHTTPServer(basicConfig EstablishedHTTPProcessConfig) (*HTTPServer, error) {
	serveAddress := fmt.Sprintf("%s:%d", basicConfig.Host, basicConfig.Port)
	listener, listenerErr := createListener(serveAddress, basicConfig.NetworkType)
	if listenerErr != nil {
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
		gracefulShutdownChannel: make(chan bool, 1),
		cancelRequests:          cancelRequests,
	}, nil
}

// Run bootstraps the server and blocks until the server is done (interrupted by signal).
func (hs *HTTPServer) Run(config server.ProcessBootstrapConfig) {
	keyboardShutdown := signals.NewKeyboardSignalHandler(hs.stopServerOnSignal)

	waitGroup := sync.WaitGroup{}
	waitGroup.Go(func() {
		hs.serveRouter()
	})

	signals.TrackSignalSafe(keyboardShutdown, hs.gracefulShutdownChannel)
	waitGroup.Wait()
}

// RegisterMiddleware adds route middleware to the global list to intercept all requests.
func (hs *HTTPServer) RegisterMiddleware(middleware *RouteMiddleware) {
	hs.basicConfig.Middlewares = sortMiddlewares(
		append(hs.basicConfig.Middlewares, middleware),
	)
}

// AddRoute adds new HTTP route that is handled by server.
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

// AddPublicRoute registers a handler that bypasses the middleware chain (for health probes).
func (hs *HTTPServer) AddPublicRoute(
	pattern string,
	handler func(http.ResponseWriter, *http.Request),
) {
	hs.router.HandleFunc(pattern, handler)
}

func (hs *HTTPServer) serveRouter() {
	serveErr := hs.server.Serve(hs.listener)
	if serveErr != nil && !errors.Is(serveErr, http.ErrServerClosed) {
		slog.Error("http listener serve failed", "error", serveErr)
	}
}

func (hs *HTTPServer) stopServerOnSignal(ctx context.Context) error {
	slog.Info("shutting down http server gracefully")

	forceShutdown, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()
	hs.shutdownWithContextAndTimeout(forceShutdown)

	return nil
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
		slog.Error("http server forced shutdown", "error", shutdownErr)
	}
}
