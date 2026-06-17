package server

type Server interface {
	Run(config ProcessBootstrapConfig)
}
