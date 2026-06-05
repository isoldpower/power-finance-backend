# ADR-0001: Fraud detection deep-path on Java + Apache Flink

- **Status:** Accepted
- **Date:** 2026-06-05
- **Deciders:** Project owner
- **Related:** [`architecture.md`](./architecture.md) — "Flink Fraud Detection", "Two-Tier Fraud Detection", "Fraud Signals Kafka"

## Context

The system design (`architecture.md`) specifies two-tier fraud detection:

- **Fast-path** — synchronous, in the Write Service, cheap rules / blocklists / freeze
  flags via Fraud Redis. Already the Write Service's concern.
- **Deep-path** — asynchronous stream processing that consumes `events.async`,
  maintains windowed state (velocity, geographic, behavioural baselines), scores
  transactions, and emits fraud signals to the `fraud.signals` Kafka topic. The
  spec names **Apache Flink** for this tier.

The deep-path needs its own home. It was confirmed it should **not** live inside the
Read Service: the Read Service is the query side of CQRS (events → terminal read
projections), whereas fraud detection flows the opposite direction — its output
(`fraud.signals`) feeds *back* into the Write Service (compensating transactions,
freeze flags). Different data-flow direction, state profile (heavy windowed state vs
stateless projection), scaling profile, and failure domain. It is therefore a separate
service.

The remaining decision is the implementation substrate. The existing stack is
polyglot:

- Write Service, Read Service — Python / Django
- Push Service — Go

So a third language is not architecturally out of place. The candidates considered:

1. **Python consumer service** — mirror the Read Service: reuse `kafka-client-py`
   (consumer loop, retry/DLQ, dedupe), `kafka-messages-proto`, and the
   `background_workers` pattern. Windowed state simulated via Redis. Lightest;
   keeps the eventual ML scorer in Python (where the ML ecosystem lives).
2. **PyFlink** — Flink semantics via a Python wrapper over the Java runtime. Closer to
   the spec, but a wrapper: serialization overhead, lagging feature support, clumsier
   UDFs.
3. **Java + Apache Flink** — the real engine. True event-time/watermarks, keyed
   windowed state in RocksDB with checkpointing, exactly-once, savepoints/rescaling.
   New language and build chain (Maven/Gradle, JVM, fat-jar), a Flink cluster in
   compose, and no reuse of the Python Kafka libraries (Kafka via Flink's connector;
   protobuf regenerated for Java).

## Decision

Build the deep-path fraud detection as a **separate service in Java on Apache Flink**.

## Rationale

This is a **learning project**, and the choice is made on learning value, not on
what is minimal for the current scale:

- **Authenticity.** Production deep-path fraud detection is overwhelmingly JVM stream
  processing (Flink / Kafka Streams / Spark) with the ML scorer plugged in. Java +
  Flink is the closest to how this is actually built. PyFlink and a hand-rolled Python
  consumer both approximate the streaming engine rather than use it.
- **Learning the engine itself.** The point of the Flink tier is the stream-processing
  machinery — event-time, watermarks, windowing, checkpointed keyed state. That cannot
  be learned authentically through a wrapper or a Redis-counter simulation.
- **Deliberately more interesting to write and maintain.** A third language on top of
  Go/Python is acknowledged as **over-engineered for this project's scale**. That
  trade-off is accepted on purpose: the project is a vehicle for learning, and a real
  Flink job is more engaging to build and own than another Python consumer.

## Consequences

**Accepted costs:**

- A new language and build toolchain (JVM, Maven/Gradle, fat-jar packaging).
- A Flink runtime in `compose.yaml` (JobManager + TaskManager + a checkpoint store).
- `kafka-messages-proto` must be generated for Java (protobuf-java); the Python
  `kafka-client-py` retry/DLQ/dedupe helpers are **not** reused — Kafka I/O goes
  through Flink's Kafka connector, and idempotency/retry follow Flink's model.
- Partitioning/ordering contract still holds: consume `events.async` (keyed by
  aggregate/user id), emit to `fraud.signals` keyed by account id so freeze/unfreeze
  sequences stay ordered per account.

**Benefits:**

- Real, transferable stream-processing experience.
- Clean separation of the fraud decision component from the read/query path.
- A natural seam for a future ML scorer (exported model loaded into the Flink job, or
  called out-of-process) without disturbing the read or write services.

## Alternatives considered

- **Fraud detection inside the Read Service** — rejected: couples a write-feedback
  loop onto the read-model projector, sharing deploy/scaling/failure domain and
  breaking the read side's terminal, never-mutating property.
- **Python consumer service** — rejected for this project's *learning* goal despite
  being the lightest and most ML-friendly option; it simulates rather than uses a
  streaming engine.
- **PyFlink** — rejected: a wrapper that obscures the very engine internals this
  service exists to learn.
