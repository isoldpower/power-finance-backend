package metrics

import (
	"net/http"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

const (
	OutcomeSuccess   = "success"
	OutcomeRetry     = "retry"
	OutcomeExhausted = "exhausted"
)

var (
	deliveryAttempts = promauto.NewCounter(prometheus.CounterOpts{
		Name: "webhook_delivery_attempts_total",
		Help: "Total number of webhook delivery attempts (HTTP sends).",
	})
	deliveryOutcomes = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "webhook_deliveries_total",
		Help: "Total number of delivery outcomes, labelled by outcome.",
	}, []string{"outcome"})
	attemptDuration = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "webhook_delivery_attempt_duration_seconds",
		Help:    "Duration of a single webhook delivery HTTP attempt.",
		Buckets: prometheus.DefBuckets,
	})
)

func init() {
	registerZeroValuedOutcomes()
}

// registerZeroValuedOutcomes initialises every outcome series at zero so they
// are exported before the first delivery is recorded.
func registerZeroValuedOutcomes() {
	deliveryOutcomes.WithLabelValues(OutcomeSuccess)
	deliveryOutcomes.WithLabelValues(OutcomeRetry)
	deliveryOutcomes.WithLabelValues(OutcomeExhausted)
}

// DeliveryAttempted records one delivery HTTP attempt.
func DeliveryAttempted() {
	deliveryAttempts.Inc()
}

// DeliveryOutcome records a terminal-or-retry delivery outcome.
func DeliveryOutcome(outcome string) {
	deliveryOutcomes.WithLabelValues(outcome).Inc()
}

// ObserveAttemptDuration records how long a delivery attempt took, in seconds.
func ObserveAttemptDuration(seconds float64) {
	attemptDuration.Observe(seconds)
}

// Handler returns the Prometheus exposition HTTP handler for the /metrics route.
func Handler() http.Handler {
	return promhttp.Handler()
}
