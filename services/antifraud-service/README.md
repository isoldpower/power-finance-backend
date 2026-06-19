# antifraud-service

Apache Flink streaming job that scores `events.async` transactions for fraud and
publishes alerts to a Kafka topic. It is the deep-path fraud detector of the
power-finance platform: a stateful, per-user keyed pipeline kept separate from
the read/write services.

## How it works

1. A Kafka source consumes the outbox topic (`events.async`).
2. Records are decoded into `OutboxEvent` POJOs; records missing the
   `event_id` / `event_type` headers are dropped.
3. The stream is keyed by the user's Clerk id (the Kafka message key) so each
   user gets independent rule state.
4. `FraudScoringEngine` runs every `FraudRule`, sums their weighted scores, and
   emits an `Alert` when the total exceeds `FRAUD_SCORE_THRESHOLD`.
5. Alerts are serialized (keyed by Clerk id) and sunk to the alerts topic
   (`fraud.alerts`), and also printed to the job's stdout.

## Project layout

Sources live under `app/src/main/java/com/powerfinance/antifraud`:

| Package   | Responsibility |
|-----------|----------------|
| `config`  | `AntifraudConfig` — runtime configuration read from the environment. |
| `io`      | Kafka source/sink, decoders and serializers (`KafkaOutboxSource`, `KafkaOutboxDecoder`, `AlertRecordSerializer`, `InflowSource`, `InflowDecoder`). |
| `rules`   | `FraudRule` and its implementations (`AmountDeviationRule`, `LowHistoryHighValueRule`, `HourlyVolumeSpikeRule`, `AlwaysAlertRule`). |
| `engine`  | `FraudScoringEngine` interface (event stream → alert stream) and its `KeyedFraudScoringEngine` implementation that aggregates rule scores per user. |
| `model`   | Flink POJOs carried through the pipeline (`OutboxEvent`, `Alert`), encapsulated behind getters/setters. |

`AlwaysAlertRule` is a demo rule that scores every event high enough to fire an
alert; it is not wired into `App` and exists only for manual end-to-end checks.

### Rules

- **AmountDeviationRule** — flags a transaction whose amount is more than
  `SIGMA_THRESHOLD` (3σ) from the user's running mean, once at least 30 samples
  exist. Uses Welford's algorithm for the running mean/variance.
- **LowHistoryHighValueRule** — flags a large transaction (> 1000) from a user
  whose cumulative history is still thin (< 100).
- **HourlyVolumeSpikeRule** — flags a user whose last-24h volume exceeds
  `SPIKE_FACTOR` (3×) the 30-day daily-average baseline, once at least 7 days of
  baseline exist. Volume is bucketed per hour and pruned to a 30-day window.

## Build & Docker

The build is a Gradle multi-project (`app` subproject) targeting Java 21.

- The shared protobuf event bindings are consumed as a **source directory**
  (`../../../libraries/kafka-messages-proto/generated/java`), wired via
  `sourceSets` in `app/build.gradle.kts`. The protobuf runtime ships in the fat
  jar.
- Flink core (`flink-streaming`, `flink-clients`, `flink-connector-base`) is
  `compileOnly` so it stays out of the fat jar — Flink provides it at runtime.
  The Gradle `run` task adds it back to the classpath for local execution.
- `com.gradleup.shadow` produces the fat (shadow) jar `app/build/libs/app-all.jar`.

The `Dockerfile` is a two-stage build (context = repo root):

1. **builder** — copies the proto library and this service, then runs
   `./gradlew clean shadowJar -x test`.
2. **runtime** — the slim job jar (Flink core excluded) is copied into
   `/opt/flink/usrlib/` so the `standalone-job` entrypoint deploys it in
   Application Mode.

`compose.yaml` includes the shared Kafka stack
(`../../infrastructure/kafka/compose.yaml`) and runs a jobmanager + taskmanager.
Inside compose the broker is reached at `kafka:9092`; host-local runs use
`localhost:9092`.

Common tasks are in the `Makefile` — run `make help` to list targets
(`build`, `run`, `test`, `build-image`, `up`, `down`, `logs`).

## Configuration

All settings are read from the environment (see `.env.example`); each has a
default baked into `AntifraudConfig`.

| Variable | Default | Description |
|----------|---------|-------------|
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka brokers. In compose the broker is `kafka:9092` (set directly in `compose.yaml`). |
| `KAFKA_OUTBOX_TOPIC` | `events.async` | Inbound outbox topic the job consumes. |
| `KAFKA_ALERTS_TOPIC` | `fraud.alerts` | Outbound topic the job posts fraud alerts to. |
| `KAFKA_GROUP_ID` | `antifraud-service` | Consumer group. `compose.yaml` substitutes it from `ANTIFRAUD_KAFKA_GROUP_ID`. |
| `FRAUD_SCORE_THRESHOLD` | `4.0` | Alert when a transaction's summed rule score exceeds this value. |
| `LOG_LEVEL` | `info` | Logging verbosity. |

The compose-only `ANTIFRAUD_UI_PORT` (default `8085`) maps the Flink web UI.
