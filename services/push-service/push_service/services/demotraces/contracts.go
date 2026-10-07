package demotraces

import "github.com/power-finance/observability-go/demosession"

const SpanEventType = "span"

type KnownServicePredicate func(serviceName string) bool

const (
	demoSessionAttributeName = demosession.SpanAttributeName
	serviceNameAttributeName = "service.name"
	unknownServiceName       = "unknown"
	unnamedServerSpanName    = "request"
)

var requestMethodAttributeNames = []string{"http.request.method", "http.method"}

var requestRouteAttributeNames = []string{"http.route"}

var forwardedSpanAttributeNames = map[string]struct{}{
	"db.system":                  {},
	"db.system.name":             {},
	"db.name":                    {},
	"db.namespace":               {},
	"db.operation":               {},
	"db.operation.name":          {},
	"messaging.system":           {},
	"messaging.operation":        {},
	"messaging.operation.type":   {},
	"messaging.destination":      {},
	"messaging.destination.name": {},
	"http.method":                {},
	"http.request.method":        {},
	"http.route":                 {},
	"http.status_code":           {},
	"http.response.status_code":  {},
	"rpc.system":                 {},
	"rpc.service":                {},
	"rpc.method":                 {},
}

type projectedSpan struct {
	TraceID              string         `json:"traceId"`
	SpanID               string         `json:"spanId"`
	ParentSpanID         string         `json:"parentSpanId,omitempty"`
	ServiceName          string         `json:"service"`
	Name                 string         `json:"name"`
	Kind                 string         `json:"kind"`
	Status               string         `json:"status"`
	StartTimeUnixNano    uint64         `json:"startTimeUnixNano,string"`
	EndTimeUnixNano      uint64         `json:"endTimeUnixNano,string"`
	DurationMilliseconds float64        `json:"durationMs"`
	Attributes           map[string]any `json:"attributes"`
}
