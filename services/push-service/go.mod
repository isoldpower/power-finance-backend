module services/push-service

go 1.26

// Local, unpublished workspace library. The filesystem replace lets `go mod
// tidy` and standalone (non-workspace) builds resolve it without a network
// fetch; go.work at the repo root covers multi-module local development.
replace github.com/power-finance/kafka-messages-proto => ../../libraries/kafka-messages-proto
