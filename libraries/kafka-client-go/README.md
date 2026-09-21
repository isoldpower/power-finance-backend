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
- `sandbox` — shared dev environment isolation: reads `sandbox-id` out of the
  W3C `baggage` header, scopes consumer group ids, and decides which process
  owns a message.
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

## Shared dev environment

The dev host runs one baseline stack; a developer's sandbox runs only the service
they changed. Which process handles a message is decided per message, from the
`sandbox-id` entry in the record's W3C `baggage` header.

```go
trafficMatcher := sandbox.NewTrafficMatcherFromEnvironment()

messageSandboxID := sandbox.ReadIDFromHeaders(message.Headers)
if !trafficMatcher.IsOwnedTraffic(messageSandboxID) {
    return nil
}
```

| Process | `SANDBOX_ID` | Owns |
| --- | --- | --- |
| baseline | empty | messages with no `sandbox-id` |
| sandbox | `nikita` | messages whose `sandbox-id` is `nikita` |

Two rules matter:

- **Return `nil` for a foreign message, do not error.** The record still has to be
  committed; a sandbox that leaves skipped offsets uncommitted stalls on the first
  message that is not its own.
- **Scope the consumer group.** `sandbox.ScopeGroupID` turns `webhook-service` into
  `webhook-service-sbx-nikita`. Without it the sandbox joins the baseline's group,
  takes partitions off it, and the baseline silently stops seeing those messages.
  `webhook-service` scopes it once in its config loader, so the Kafka group and the
  Postgres dedupe group — which is keyed by group id — stay in step.

`push-service` consumes grouplessly by design, so it only needs the filter.

**Trace export is not wired on the Go side yet.** The `sandbox` package is
standard-library only and deliberately carries no OpenTelemetry dependency; the
Go services propagate no spans until the OTel Go SDK is added.
