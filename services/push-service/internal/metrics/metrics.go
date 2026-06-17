package metrics

import (
	"net/http"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

const (
	dropReasonMalformed  = "malformed"
	dropReasonSlowClient = "slow_client"
)

var (
	kafkaEventsReceived = promauto.NewCounter(prometheus.CounterOpts{
		Name: "push_kafka_events_received_total",
		Help: "Total number of events received from the Kafka broadcast topic.",
	})
	eventsProjected = promauto.NewCounter(prometheus.CounterOpts{
		Name: "push_events_projected_total",
		Help: "Total number of events projected and forwarded to the fanout.",
	})
	eventsDropped = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "push_events_dropped_total",
		Help: "Total number of events dropped, labelled by reason.",
	}, []string{"reason"})
	activeSubscribers = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "push_active_subscribers",
		Help: "Current number of connected SSE subscribers.",
	})
)

func init() {
	registerZeroValuedDropReasons()
}

// registerZeroValuedDropReasons initialises every drop-reason series at zero so
// they are exported before the first drop is recorded.
func registerZeroValuedDropReasons() {
	eventsDropped.WithLabelValues(dropReasonMalformed)
	eventsDropped.WithLabelValues(dropReasonSlowClient)
}

// KafkaEventReceived records one event consumed from the Kafka topic.
func KafkaEventReceived() {
	kafkaEventsReceived.Inc()
}

// EventProjected records one event successfully forwarded to the fanout.
func EventProjected() {
	eventsProjected.Inc()
}

// EventDroppedMalformed records an event dropped because it failed projection.
func EventDroppedMalformed() {
	eventsDropped.WithLabelValues(dropReasonMalformed).Inc()
}

// EventDroppedSlowClient records an event dropped because a client buffer was full.
func EventDroppedSlowClient() {
	eventsDropped.WithLabelValues(dropReasonSlowClient).Inc()
}

// SubscriberAdded increments the active subscriber gauge.
func SubscriberAdded() {
	activeSubscribers.Inc()
}

// SubscriberRemoved decrements the active subscriber gauge.
func SubscriberRemoved() {
	activeSubscribers.Dec()
}

// SubscribersReset zeroes the active subscriber gauge, used on fanout shutdown.
func SubscribersReset() {
	activeSubscribers.Set(0)
}

// Handler returns the Prometheus exposition HTTP handler for the /metrics route.
func Handler() http.Handler {
	return promhttp.Handler()
}
