package kafka

import (
	"context"
	"errors"
	"testing"

	kafkaclient "github.com/power-finance/kafka-client-go"
	"github.com/twmb/franz-go/pkg/kgo"
)

type fakeGroupConsumer struct {
	pendingFetches []kgo.Fetches
	committed      []*kgo.Record
	commitError    error
	closed         bool
	stopPolling    context.CancelFunc
}

func (f *fakeGroupConsumer) PollFetches(ctx context.Context) kgo.Fetches {
	if len(f.pendingFetches) == 0 {
		f.stopPolling()
		return kgo.Fetches{}
	}

	nextFetches := f.pendingFetches[0]
	f.pendingFetches = f.pendingFetches[1:]
	return nextFetches
}

func (f *fakeGroupConsumer) CommitRecords(ctx context.Context, records ...*kgo.Record) error {
	if f.commitError != nil {
		return f.commitError
	}
	f.committed = append(f.committed, records...)
	return nil
}

func (f *fakeGroupConsumer) Close() {
	f.closed = true
}

type recordingHandler struct {
	handled      []kafkaclient.ConsumedMessage
	handlerError error
}

func (rh *recordingHandler) Handle(ctx context.Context, message kafkaclient.ConsumedMessage) error {
	rh.handled = append(rh.handled, message)
	return rh.handlerError
}

func fetchesWithRecords(records ...*kgo.Record) kgo.Fetches {
	return kgo.Fetches{{
		Topics: []kgo.FetchTopic{{
			Topic:      "events.async",
			Partitions: []kgo.FetchPartition{{Records: records}},
		}},
	}}
}

func runLoopUntilDrained(consumer *fakeGroupConsumer, handler *recordingHandler) {
	loopContext, cancel := context.WithCancel(context.Background())
	consumer.stopPolling = cancel

	NewConsumerLoop(consumer, handler).Run(loopContext)
}

func TestLoopHandlesAndCommitsEachRecord(t *testing.T) {
	firstRecord := &kgo.Record{Topic: "events.async", Value: []byte("first")}
	secondRecord := &kgo.Record{Topic: "events.async", Value: []byte("second")}
	consumer := &fakeGroupConsumer{
		pendingFetches: []kgo.Fetches{fetchesWithRecords(firstRecord, secondRecord)},
	}
	handler := &recordingHandler{}

	runLoopUntilDrained(consumer, handler)

	if len(handler.handled) != 2 {
		t.Fatalf("expected 2 handled messages, got %d", len(handler.handled))
	}
	if string(handler.handled[0].Value) != "first" || string(handler.handled[1].Value) != "second" {
		t.Fatalf("expected in-order delivery, got %+v", handler.handled)
	}
	if len(consumer.committed) != 2 {
		t.Fatalf("expected 2 commits, got %d", len(consumer.committed))
	}
	if !consumer.closed {
		t.Fatal("expected consumer to be closed on loop exit")
	}
}

func TestLoopSkipsCommitWhenHandlerFails(t *testing.T) {
	record := &kgo.Record{Topic: "events.async", Value: []byte("payload")}
	consumer := &fakeGroupConsumer{
		pendingFetches: []kgo.Fetches{fetchesWithRecords(record)},
	}
	handler := &recordingHandler{handlerError: errors.New("publish to DLQ failed")}

	runLoopUntilDrained(consumer, handler)

	if len(handler.handled) != 1 {
		t.Fatalf("expected 1 handled message, got %d", len(handler.handled))
	}
	if len(consumer.committed) != 0 {
		t.Fatalf("expected no commits so the message is redelivered, got %d", len(consumer.committed))
	}
}

func TestLoopContinuesAfterCommitFailure(t *testing.T) {
	record := &kgo.Record{Topic: "events.async", Value: []byte("payload")}
	consumer := &fakeGroupConsumer{
		pendingFetches: []kgo.Fetches{
			fetchesWithRecords(record),
			fetchesWithRecords(record),
		},
		commitError: errors.New("rebalance in progress"),
	}
	handler := &recordingHandler{}

	runLoopUntilDrained(consumer, handler)

	if len(handler.handled) != 2 {
		t.Fatalf("expected loop to keep consuming after commit failure, got %d", len(handler.handled))
	}
}

func TestLoopStopsMidBatchWhenContextCancelled(t *testing.T) {
	firstRecord := &kgo.Record{Topic: "events.async", Value: []byte("first")}
	secondRecord := &kgo.Record{Topic: "events.async", Value: []byte("second")}
	consumer := &fakeGroupConsumer{
		pendingFetches: []kgo.Fetches{fetchesWithRecords(firstRecord, secondRecord)},
	}

	loopContext, cancel := context.WithCancel(context.Background())
	consumer.stopPolling = cancel
	stopAfterFirstMessage := &cancellingHandler{cancel: cancel}

	NewConsumerLoop(consumer, stopAfterFirstMessage).Run(loopContext)

	if stopAfterFirstMessage.handledCount != 1 {
		t.Fatalf("expected to stop after first message, got %d", stopAfterFirstMessage.handledCount)
	}
	if !consumer.closed {
		t.Fatal("expected consumer to be closed on shutdown")
	}
}

type cancellingHandler struct {
	cancel       context.CancelFunc
	handledCount int
}

func (ch *cancellingHandler) Handle(ctx context.Context, message kafkaclient.ConsumedMessage) error {
	ch.handledCount++
	ch.cancel()
	return nil
}
