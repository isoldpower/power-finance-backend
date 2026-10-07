package demotraces

import (
	"encoding/hex"
	"encoding/json"
	"fmt"
	"iter"
	"log/slog"
	"strings"

	commonv1 "go.opentelemetry.io/proto/otlp/common/v1"
	tracev1 "go.opentelemetry.io/proto/otlp/trace/v1"
	"google.golang.org/protobuf/proto"

	"services/push-service/internal/metrics"
	"services/push-service/push_service/types"
)


const nanosecondsPerMillisecond = 1_000_000

func ProjectDemoSpanEvents(
	tracesPayload []byte,
	isKnownService KnownServicePredicate,
) ([]types.OutboxEvent, error) {
	var tracesData tracev1.TracesData
	if unmarshalErr := proto.Unmarshal(tracesPayload, &tracesData); unmarshalErr != nil {
		return nil, fmt.Errorf("demo traces: decode otlp payload: %w", unmarshalErr)
	}

	var projectedEvents []types.OutboxEvent
	for _, resourceSpans := range tracesData.GetResourceSpans() {
		serviceName := readServiceName(resourceSpans)
		if !isKnownService(serviceName) {
			recordUnknownServiceSpansDropped(serviceName, resourceSpans)
		} else {
            resourceEvents, projectErr := projectResourceSpans(serviceName, resourceSpans)
            if projectErr != nil {
                return nil, projectErr
            }

            projectedEvents = append(projectedEvents, resourceEvents...)
		}
	}

	return projectedEvents, nil
}

func projectResourceSpans(
	serviceName string,
	resourceSpans *tracev1.ResourceSpans,
) ([]types.OutboxEvent, error) {
	var resourceEvents []types.OutboxEvent
	for span := range spansOfResource(resourceSpans) {
		projectedEvent, isDemoSpan, projectErr := projectSpan(serviceName, span)
		if projectErr != nil {
			return nil, projectErr
		}

		if isDemoSpan {
			resourceEvents = append(resourceEvents, projectedEvent)
		}
	}

	return resourceEvents, nil
}

func spansOfResource(resourceSpans *tracev1.ResourceSpans) iter.Seq[*tracev1.Span] {
	return func(yield func(*tracev1.Span) bool) {
		for _, scopeSpans := range resourceSpans.GetScopeSpans() {
			for _, span := range scopeSpans.GetSpans() {
				if !yield(span) {
					return
				}
			}
		}
	}
}

func carriesDemoSession(span *tracev1.Span) bool {
	for _, keyValue := range span.GetAttributes() {
		if keyValue.GetKey() == demoSessionAttributeName && keyValue.GetValue().GetStringValue() != "" {
			return true
		}
	}

	return false
}

func projectSpan(serviceName string, span *tracev1.Span) (types.OutboxEvent, bool, error) {
	demoSessionIdentifier := ""
	forwardedAttributes := make(map[string]any)
	for _, keyValue := range span.GetAttributes() {
		if keyValue.GetKey() == demoSessionAttributeName {
			demoSessionIdentifier = keyValue.GetValue().GetStringValue()
		} else if _, isForwarded := forwardedSpanAttributeNames[keyValue.GetKey()]; isForwarded {
			forwardedAttributes[keyValue.GetKey()] = readAttributeValue(keyValue.GetValue())
		}
	}

	if demoSessionIdentifier == "" {
		return types.OutboxEvent{}, false, nil
	}

	spanIdentifier := hex.EncodeToString(span.GetSpanId())
	encodedSpan, encodeErr := json.Marshal(projectedSpan{
		TraceID:              hex.EncodeToString(span.GetTraceId()),
		SpanID:               spanIdentifier,
		ParentSpanID:         hex.EncodeToString(span.GetParentSpanId()),
		ServiceName:          serviceName,
		Name:                 sanitizeSpanName(span, forwardedAttributes),
		Kind:                 spanKindName(span.GetKind()),
		Status:               spanStatusName(span.GetStatus().GetCode()),
		StartTimeUnixNano:    span.GetStartTimeUnixNano(),
		EndTimeUnixNano:      span.GetEndTimeUnixNano(),
		DurationMilliseconds: spanDurationMilliseconds(span),
		Attributes:           forwardedAttributes,
	})
	if encodeErr != nil {
		return types.OutboxEvent{}, false, fmt.Errorf("demo traces: encode span: %w", encodeErr)
	}

	return types.OutboxEvent{
		EventID:   spanIdentifier,
		EventType: SpanEventType,
		UserID:    demoSessionIdentifier,
		Payload:   encodedSpan,
	}, true, nil
}

func recordUnknownServiceSpansDropped(serviceName string, resourceSpans *tracev1.ResourceSpans) {
	droppedSpanCount := 0
	for span := range spansOfResource(resourceSpans) {
		if carriesDemoSession(span) {
			metrics.EventDroppedUnknownService()
			droppedSpanCount++
		}
	}

	if droppedSpanCount > 0 {
		slog.Debug(
			"dropping demo spans from a service missing from the infrastructure topology",
			"service", serviceName,
			"dropped_span_count", droppedSpanCount,
		)
	}
}

func sanitizeSpanName(span *tracev1.Span, forwardedAttributes map[string]any) string {
	requestMethod := readFirstStringAttribute(forwardedAttributes, requestMethodAttributeNames)
	requestRoute := readFirstStringAttribute(forwardedAttributes, requestRouteAttributeNames)

	if requestRoute != "" {
		return strings.TrimSpace(requestMethod + " " + requestRoute)
	} else if span.GetKind() == tracev1.Span_SPAN_KIND_SERVER {
		if requestMethod != "" {
			return requestMethod
		}

		return unnamedServerSpanName
	}

	return span.GetName()
}

func readFirstStringAttribute(forwardedAttributes map[string]any, attributeNames []string) string {
	for _, attributeName := range attributeNames {
		if attributeValue, isString := forwardedAttributes[attributeName].(string); isString && attributeValue != "" {
			return attributeValue
		}
	}

	return ""
}

func readServiceName(resourceSpans *tracev1.ResourceSpans) string {
	for _, keyValue := range resourceSpans.GetResource().GetAttributes() {
		if keyValue.GetKey() == serviceNameAttributeName {
			return keyValue.GetValue().GetStringValue()
		}
	}

	return unknownServiceName
}

func readAttributeValue(anyValue *commonv1.AnyValue) any {
	switch typedValue := anyValue.GetValue().(type) {
	case *commonv1.AnyValue_StringValue:
		return typedValue.StringValue
	case *commonv1.AnyValue_IntValue:
		return typedValue.IntValue
	case *commonv1.AnyValue_DoubleValue:
		return typedValue.DoubleValue
	case *commonv1.AnyValue_BoolValue:
		return typedValue.BoolValue
	default:
		return nil
	}
}

func spanDurationMilliseconds(span *tracev1.Span) float64 {
	if span.GetEndTimeUnixNano() < span.GetStartTimeUnixNano() {
		return 0
	}

    spanUnixGap := span.GetEndTimeUnixNano() - span.GetStartTimeUnixNano()
	return float64(spanUnixGap) / nanosecondsPerMillisecond
}

func spanKindName(spanKind tracev1.Span_SpanKind) string {
	switch spanKind {
	case tracev1.Span_SPAN_KIND_SERVER:
		return "server"
	case tracev1.Span_SPAN_KIND_CLIENT:
		return "client"
	case tracev1.Span_SPAN_KIND_PRODUCER:
		return "producer"
	case tracev1.Span_SPAN_KIND_CONSUMER:
		return "consumer"
	default:
		return "internal"
	}
}

func spanStatusName(statusCode tracev1.Status_StatusCode) string {
	switch statusCode {
	case tracev1.Status_STATUS_CODE_OK:
		return "ok"
	case tracev1.Status_STATUS_CODE_ERROR:
		return "error"
	default:
		return "unset"
	}
}
