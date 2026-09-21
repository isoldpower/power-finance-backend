# ADR-0003: Baseline consumers cover sandbox traffic that no sandbox consumer claims

- **Status:** Accepted
- **Date:** 2026-09-14
- **Deciders:** Project owner
- **Related:** [`adr-0002-shared-dev-environment.md`](./adr-0002-shared-dev-environment.md), [`../libraries/kafka-consumer-py/README.md`](../libraries/kafka-consumer-py/README.md), [`../infrastructure/dev-host/README.md`](../infrastructure/dev-host/README.md)

## Context

ADR-0002 gave every sandbox an identity carried in OpenTelemetry baggage, and gave
consumers a filter that compares the message's `sandbox-id` with their own by strict
equality. A baseline consumer therefore takes untagged traffic only, and a sandbox
consumer takes its own tag only.

That rule is right about one thing and wrong about another.

**Right:** exactly one consumer must process each event per datastore. A baseline
and a sandbox consumer are in different Kafka groups, so both receive every message,
and non-isolated sandboxes share the dev host's databases. Several projections are
deltas rather than upserts — `apply_container_delta`, and the Painless
`balance = balance + delta` behind an indexed wallet — so a second application
silently corrupts a balance. The dedupe table does not help: it is keyed
`(consumer_group, event_id)`, and a sandbox consumer's group is a different group.

**Wrong:** the rule made the whole stack ignore a sandbox's events, not just the one
service the developer was running. Working on read-service and writing a transaction
through the gateway with `X-Sandbox: nikita` meant ai-service never booked its
postings, the automation engine never evaluated it, and the webhook consumer never
delivered it. Those events are not queued for later — the filter is a permanent skip,
so the developer either ran every service or reconciled the gaps by hand afterwards.

Strict equality also cuts the other way, and that part must stay: a sandbox consumer
runs the developer's edited code, so it must never process the team's baseline traffic
into shared datastores.

Three ways to tell a baseline consumer that a sandbox is covering a service:

- **A — a registry in gateway-redis.** Sandbox processes register a claim key with a
  TTL, the baseline reads it. Explicit, but it is a second copy of a fact, it needs
  lifecycle management, and ai-service's and write-service's consumers use no Redis
  at all today.
- **B — a liveness heartbeat.** Same, refreshed every few seconds. Rejected outright:
  a consumer that is briefly down loses its claim, the baseline processes the events,
  and the consumer then resumes from its own committed offset and applies them a
  second time. It converts a restart into the one failure mode that corrupts data.
- **C — ask Kafka.** A sandbox consumer's group id is derived from the baseline's by
  `resolve_sandbox_scoped_group_id`, so the baseline can name the group its
  counterpart *would* use and check whether that group exists.

## Decision

**Option C. The baseline processes untagged traffic plus any tagged traffic whose
sandbox is not running a consumer for that service; sandbox consumers keep taking
only their own tag.**

- `BaselineFallbackTrafficPolicy` asks `KafkaSandboxGroupRegistry` whether
  `<own-group>-sbx-<sandbox>` exists, caching the group list for ten seconds.
- `StrictSandboxTrafficPolicy` is the previous behaviour, unchanged, for sandboxes.
- `build_sandbox_traffic_policy` picks between them from `SANDBOX_ID`.

The claim is **group existence, not member liveness**. A stopped consumer leaves its
group behind with committed offsets, so the claim survives a restart and its owner
resumes from where it left off. Kafka expires the group on its own once the offsets
pass `offsets.retention.minutes` (seven days by default), so nothing registers,
heartbeats, or has to be cleaned up.

When the group listing fails, the previous answer stands and an unknown sandbox reads
as claimed — the baseline skips. A gap is recoverable by replay or backfill; a double
application of a delta is not.

## Consequences

- A developer runs only the service they changed. Everything else keeps working off
  the baseline, continuously, with nothing to reconcile afterwards.
- Sandbox data reaches the shared datastores through baseline consumers for services
  the developer is not running. That was already true of non-isolated sandboxes,
  which share those datastores by design.
- Baseline consumers make a `ListGroups` call at most once per ten seconds. Sandbox
  consumers make none: their answer needs no lookup.
- `SandboxTrafficPolicy.is_owned_traffic` is now async, since answering can require a
  broker round trip.
- **One hole remains: the first ever start of a sandbox consumer.** Until its group
  exists the baseline legitimately processes that sandbox's events; starting the
  consumer afterwards with `--from-beginning` reapplies them. Start the sandbox before
  exercising it — `make <service> sandbox` does this in one step — and the window
  closes after the first run.
- An isolated sandbox (`ISOLATED=1`) still sees only its own tagged events, because
  its consumer is strict. Its datastores are its own, so the baseline's coverage of
  those same events does not collide with it.
