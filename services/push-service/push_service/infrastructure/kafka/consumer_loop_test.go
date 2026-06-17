package kafka

import (
	"context"
	"testing"

	kafkaclient "github.com/power-finance/kafka-client-go"
	"github.com/twmb/franz-go/pkg/kgo"

	"services/push-service/internal/health"
)

type fakeBroadcastConsumer struct {
	pendingFetches []kgo.Fetches
	closed         bool
	stopPolling    context.CancelFunc
}

func (f *fakeBroadcastConsumer) PollFetches(ctx context.Context) kgo.Fetches {
	if len(f.pendingFetches) == 0 {
		f.stopPolling()
		return kgo.Fetches{}
	}

	nextFetches := f.pendingFetches[0]
	f.pendingFetches = f.pendingFetches[1:]
	return nextFetches
}

func (f *fakeBroadcastConsumer) Close() {
	f.closed = true
}

func fetchesWithRecords(records ...*kgo.Record) kgo.Fetches {
	return kgo.Fetches{{
		Topics: []kgo.FetchTopic{{
			Topic:      "events.async",
			Partitions: []kgo.FetchPartition{{Records: records}},
		}},
	}}
}

func recordingHandler(handled *[]kafkaclient.ConsumedMessage, handlerError error) MessageHandlerFunc {
	return func(ctx context.Context, message kafkaclient.ConsumedMessage) error {
		*handled = append(*handled, message)
		return handlerError
	}
}

func runLoopUntilDrained(consumer *fakeBroadcastConsumer, handle MessageHandlerFunc) {
	loopContext, cancel := context.WithCancel(context.Background())
	consumer.stopPolling = cancel

	NewConsumerLoop(consumer, handle, health.NewProbe()).Run(loopContext)
}

func TestLoopHandlesEachRecordInOrder(t *testing.T) {
	firstRecord := &kgo.Record{Topic: "events.async", Value: []byte("first")}
	secondRecord := &kgo.Record{Topic: "events.async", Value: []byte("second")}
	consumer := &fakeBroadcastConsumer{
		pendingFetches: []kgo.Fetches{fetchesWithRecords(firstRecord, secondRecord)},
	}

	var handled []kafkaclient.ConsumedMessage
	runLoopUntilDrained(consumer, recordingHandler(&handled, nil))

	if len(handled) != 2 {
		t.Fatalf("expected 2 handled messages, got %d", len(handled))
	}
	if string(handled[0].Value) != "first" || string(handled[1].Value) != "second" {
		t.Fatalf("expected in-order delivery, got %+v", handled)
	}
	if !consumer.closed {
		t.Fatal("expected consumer to be closed on loop exit")
	}
}

func TestLoopContinuesAfterHandlerFailure(t *testing.T) {
	record := &kgo.Record{Topic: "events.async", Value: []byte("payload")}
	consumer := &fakeBroadcastConsumer{
		pendingFetches: []kgo.Fetches{
			fetchesWithRecords(record),
			fetchesWithRecords(record),
		},
	}

	var handled []kafkaclient.ConsumedMessage
	runLoopUntilDrained(consumer, recordingHandler(&handled, context.DeadlineExceeded))

	if len(handled) != 2 {
		t.Fatalf("expected loop to keep consuming after handler failure, got %d", len(handled))
	}
}

func TestLoopStopsMidBatchWhenContextCancelled(t *testing.T) {
	firstRecord := &kgo.Record{Topic: "events.async", Value: []byte("first")}
	secondRecord := &kgo.Record{Topic: "events.async", Value: []byte("second")}
	consumer := &fakeBroadcastConsumer{
		pendingFetches: []kgo.Fetches{fetchesWithRecords(firstRecord, secondRecord)},
	}

	loopContext, cancel := context.WithCancel(context.Background())
	consumer.stopPolling = cancel

	handledCount := 0
	stopAfterFirstMessage := func(ctx context.Context, message kafkaclient.ConsumedMessage) error {
		handledCount++
		cancel()
		return nil
	}

	NewConsumerLoop(consumer, stopAfterFirstMessage, health.NewProbe()).Run(loopContext)

	if handledCount != 1 {
		t.Fatalf("expected to stop after first message, got %d", handledCount)
	}
	if !consumer.closed {
		t.Fatal("expected consumer to be closed on shutdown")
	}
}

func TestLoopTogglesReadinessProbe(t *testing.T) {
	probe := health.NewProbe()
	consumer := &fakeBroadcastConsumer{}

	loopContext, cancel := context.WithCancel(context.Background())
	consumer.stopPolling = func() {
		if !probe.IsReady() {
			t.Error("expected probe to be ready while the loop is running")
		}
		cancel()
	}

	var handled []kafkaclient.ConsumedMessage
	NewConsumerLoop(consumer, recordingHandler(&handled, nil), probe).Run(loopContext)

	if probe.IsReady() {
		t.Fatal("expected probe to be unready after the loop exits")
	}
}
