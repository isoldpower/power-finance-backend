package http

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/power-finance/observability-go/sandbox"
	"github.com/power-finance/observability-go/tracing"

	"services/push-service/internal/health"
	"services/push-service/push_service/types"
)

type audienceRecordingStream struct {
	types.NotificationsStream
	recordedAudience types.StreamAudience
}

func (stream *audienceRecordingStream) Subscribe(
	audience types.StreamAudience,
) (<-chan types.OutboxEvent, func(), bool) {
	stream.recordedAudience = audience
	return nil, func() {}, false
}

func TestNotificationsStreamSubscribesWithTheConnectionSandbox(t *testing.T) {
	t.Setenv(tracing.EnvironmentVariableSDKDisabled, "true")
	if _, _, configureErr := tracing.Configure(context.Background(), "push-service-test"); configureErr != nil {
		t.Fatal(configureErr)
	}
	recordingStream := &audienceRecordingStream{}
	presentation := NewHttpPresentation(recordingStream, types.DemoSurface{}, health.NewProbe())

	requestContext := WithAuthenticatedUserID(
		sandbox.AttachID(context.Background(), "nikita"),
		"user_2abc",
	)
	request := httptest.NewRequest(http.MethodGet, "/api/v1/notifications/stream", nil).WithContext(requestContext)
	presentation.HandleGetNotifications(httptest.NewRecorder(), request)

	expectedAudience := types.StreamAudience{ExternalUserID: "user_2abc", SandboxID: "nikita"}
	if recordingStream.recordedAudience != expectedAudience {
		t.Fatalf("expected %+v, got %+v", expectedAudience, recordingStream.recordedAudience)
	}
}
