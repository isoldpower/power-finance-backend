# kafka-client-go

Shared Kafka helpers for the Go services: a consumer-side message handler with
in-process retries, retry-topic scheduling, DLQ routing and idempotent dedupe,
plus a publisher and header utilities. Built on [franz-go](https://github.com/twmb/franz-go).

## Packages

- `consumer` — `MessageHandler` orchestrates per-message processing: dedupe →
  in-process retries → terminal routing (retry topic or DLQ).
- `consumer/dedupe` — `Store` (`InMemoryStore`, `PostgresStore`) and the `Gate`
  that skips already-consumed events.
- `publisher` — `KafkaPublisher` plus `RetryPublisher` / `DLQPublisher` that
  republish with diagnostic headers.
- `headers` — typed Kafka header encode/decode and `Merge`.
- `envelope` — well-known envelope header names.
- root package — error sentinels (`ErrPoison`, `ErrTransient`, `ErrKafkaHandler`)
  and `ErrorClass`.

## Failure handling

The handler classifies each user-handler error:

- `ErrPoison` (or non-retryable) → routed straight to the DLQ, no retry.
- `ErrTransient` / `RetryPolicy.Retryable` → retried in-process up to
  `MaxInProcessAttempts` with capped linear backoff; once exhausted the message
  is republished to the retry topic (up to `MaxRetryTopicAttempts`, exponential
  backoff with jitter) and finally to the DLQ.
- shutdown (cancelled context) → returned to the caller without routing, leaving
  the offset uncommitted for redelivery.

## Deduplication

`MessageHandler` checks the `DedupeStore` before processing and marks the event
id after a **successful** handle, so a redelivery (e.g. after a rebalance) is
skipped. Marking happens only on success — retry-scheduled and DLQ'd events are
never marked, since their retries must still run.

The default auto-mark is best-effort: a mark failure is logged, not returned.
For exactly-once, mark transactionally inside your own handler with
`dedupe.WithMarkExecutor(tx)` so the mark commits atomically with your write.

A `DedupeStore` requires an `EventID` extractor; configuring one without the
other disables dedupe and logs a warning.

## Usage

```go
handler := consumer.NewMessageHandler(userHandler, consumer.MessageHandlerConfig{
    Policy:         consumer.DefaultRetryPolicy(),
    RetryPublisher: publisher.NewRetryPublisher(kafkaPublisher, "events.retry"),
    DLQPublisher:   publisher.NewDLQPublisher(kafkaPublisher, "events.dlq"),
    DedupeStore:    dedupe.NewPostgresStore(pool, "my-consumer-group"),
    EventID:        myEventIDExtractor,
})
```

The `kafka_consumed_events` table for `PostgresStore` is created by
`dedupe.CreateTableSQL`.
