# ADR-0002: Shared dev environment — one baseline plus per-developer sandboxes, routed by OpenTelemetry baggage

- **Status:** Accepted
- **Date:** 2026-09-12
- **Deciders:** Project owner
- **Related:** [`architecture.md`](./architecture.md), [`../infrastructure/README.md`](../infrastructure/README.md) — "Tracing", "Debezium", [`../libraries/observability-py/README.md`](../libraries/observability-py/README.md)

## Context

Development moves onto a shared host: a MacBook M2 Pro with 16 GB of RAM. The full
stack is roughly thirty containers — Kafka, Debezium Connect, Elasticsearch,
Kibana, a Flink pair, four Postgres instances, three Redis instances, ImmuDB, Kong
and around a dozen Python service and consumer processes. Measured heap-by-heap it
comes to about 12–13 GB untuned, and macOS itself takes 3–4 GB.

That single number decides the architecture: **the host holds exactly one copy of
the stack.** Giving each developer their own is not tight, it is impossible.

The industry answer to the same problem, arrived at for cost rather than for RAM,
is application-layer isolation: Lyft's Staging Overrides, Uber's SLATE, the pattern
Signadot productises. One shared baseline; a request carries a marker; only the
service under test is duplicated; the marker decides who serves the request.

Four options were considered:

- **A — a bespoke `sandbox_id` field.** Thread one dev-only column, argument and
  header through the outbox and every consumer. Cheapest to write, and it carries
  exactly one value forever; the next thing needing propagation repeats the work.
- **B — generic context propagation.** Propagate W3C `traceparent` + `baggage`, and
  make `sandbox-id` one baggage entry.
- **C — a full stack per developer.** Architecturally clean, zero production code
  touched, and dead on arrival at ~9 GB a copy.
- **D — no isolation.** One shared dev stack, developers coordinate verbally. Zero
  code. Entirely reasonable at one or two developers; it breaks down when two
  people need the stack at once.

## Decision

**One baseline stack, per-developer sandboxes, isolation carried by OpenTelemetry
baggage — option B.**

- `docker compose -p pf-baseline` runs every service at `main`, tuned to ~9 GB
  (ES/Kafka heaps capped, one Flink slot, smaller Postgres buffers, Kibana scaled to
  zero). It is always up and nobody edits it.
- A sandbox runs **only** the changed service as a `pf-sbx-<name>` compose project
  on the host, pointed at the baseline's Kafka, Postgres, Elasticsearch and Redis,
  with the developer's source bind-mounted so an edit is live in about a second.
- Kong's `sandbox-router` plugin resolves a sandbox id and overrides the upstream,
  falling back to the baseline whenever there is no id, no registered route, or
  Redis is unhappy.
- Events carry `traceparent`, `tracestate` and `baggage` from the producing request
  through the outbox row and out as Kafka record headers. Consumers re-attach that
  context; `sandbox-id` in the baggage decides who owns the message.
- No remote IDE workspaces. Baseline plus macOS leaves around 3 GB, which holds
  sandboxes, not editors. This is settled by RAM, not by preference.

## Consequences

**The honest cost: a test-time concern now lives in production code paths.**
`build_outbox_entry` captures trace context, the outbox tables carry three extra
columns, the consumer library grew two decorating processors, and a Lua plugin in
the real gateway reads the `baggage` header. Lyft and Uber pay the same tax — their
Envoy filters and header propagation run in production too. There is no version of
shared-baseline isolation where the application does not cooperate.

**What makes the tax worth paying.** The propagation is standard and general, not a
sandbox hack:

- The correlation id used to die at the outbox. Debezium publishes rows
  asynchronously, the outbox table had no propagation columns, and the connector's
  header placement did not mention any — so every event reaching the read, push, ai
  and webhook services began a fresh trace. Write-side and read-side logs could not
  be joined at all. Fixing that hop was worth doing on its own merits.
- `get_correlation_id()` now returns the active trace id, so the `request_id` a
  client sees in a response envelope opens a real trace in Jaeger.
- Future propagated values — tenant, feature flag, idempotency key — cost one
  baggage key rather than another migration.

**Baggage, never the trace id.** Baggage propagates regardless of the sampling
decision, and a trace id is unique per request, so there is nothing stable to match
a route against. A sampling change must never change routing.

**Consumer groups are load-bearing.** A sandbox consumer must run under
`<group>-sbx-<sandbox>`, and its dedupe store must use the same scoped value. An
unscoped sandbox joins the baseline's group and takes partitions off it; an unscoped
dedupe store lets one side mark the other's messages as already consumed. Both
failures are silent.

**Accepted limits.**

- One baseline means one failure domain: break `main` and every developer's
  dependency layer is broken until it is fixed. Every company on this pattern
  accepts that.
- Concurrent schema migrations are the real ceiling. A sandbox testing a migration
  needs its own Postgres container; roughly two of those fit at once.
- Tracing is off unless `OTEL_EXPORTER_OTLP_ENDPOINT` is set, so laptop-only runs
  stay silent — and produce no spans.
- The Go services (`push-service`, `webhook-service`) carry sandbox isolation but
  **no trace export yet**: their `sandbox` package is standard-library only. Adding
  the OpenTelemetry Go SDK is outstanding work.

**Six defects only a running stack revealed.** The design held; the integration
details did not, and none of these would have been caught by tests:

1. The service Dockerfiles copy a whitelist of libraries, so `observability-py` was
   missing from the images and `uv sync` failed at build.
2. Kong 3.7's `opentelemetry` plugin field is `endpoint`, not `traces_endpoint` —
   the gateway would not have booted.
3. Jaeger's Badger volume mounts root-owned while Jaeger runs as uid 10001; it
   needs an init container to chown it.
4. Sandboxes reusing baseline service names gave `write-service` two DNS answers on
   the shared network, so roughly a third of *untagged* traffic would have landed in
   a developer's sandbox — the exact failure the design exists to prevent. Fixed by
   naming sandbox services `sbx-<service>` via `extends` and routing by container IP.
5. `ADD --chmod=644` left `/opt/otel` untraversable for the `flink` user the Flink
   entrypoint drops to, crash-looping the antifraud pair.
6. The OpenTelemetry Java agent defaults to `http/protobuf` and was pointed at the
   gRPC port, so it exported nothing.

And one behavioural defect in the tracing itself: **OpenTelemetry's Django
instrumentation does not make its span current under ASGI**, because it attaches
context inside a `sync_to_async` call whose context changes asgiref discards. Every
outbox row came out with NULL propagation columns until the ASGI/WSGI application
was wrapped directly. The lesson generalises: instrumenting Django is not the same
as instrumenting the server that runs it.

**Verified end to end on a live stack**: a write produced one 20-span trace spanning
`write-service` and `read-write-consumer`, the read-side spans parented to the
write-side span that wrote the outbox row; and with a sandbox running, the baseline
consumer saw only untagged messages while the sandbox consumer saw only its own.

**Revised again 2026-09-13: the developer's service runs on their own machine.**
The revision below collapsed to a host-side container on the grounds that the loop
needed a fast reload, which a bind mount supplies. That holds, but it forces the
source to live on the dev host, and an ordinary clone-edit-run loop with a local
debugger is worth more than the uniformity gained. So a locally-run service is the
primary path again, with two corrections to how it was first designed:

- **SSH tunnels rather than published ports.** `make devhost-tunnels` forwards the
  baseline's infrastructure to the laptop's localhost and forwards one local port
  back for the gateway. `BIND_ADDRESS` stays loopback and only the gateway is
  published, so the earlier trade of "local execution costs you exposure" does not
  apply. `KAFKA_EXTERNAL_HOST=localhost` is *correct* under tunnelling, because a
  client follows the broker's advertisement back into its own tunnel.
- **Most work needs no gateway route at all.** Hitting the local service directly
  with `X-User-Id` exercises everything but the edge; the reverse tunnel and
  `host-route-laptop` are only for testing through Clerk auth, rate limits and
  read-fallback.

The host-side container mode stays for the compiled services, for anything that
should outlive a closed laptop, and for `ISOLATED=1` datastore work. The accepted
cost of running locally is environment drift — a laptop's interpreter is not the
image's — so CI remains the arbiter before merge.

**Revised 2026-09-15: `ISOLATED=1` is no longer a reason to use container mode.**
The flag reached only `host-sandbox-up`, so a laptop testing a migration had to either
move to the dev host or apply it to the shared database — and since nothing said
so, the second is what happened. `sandbox-env` now honours the flag (pointing the
database lines at a laptop-local Postgres and prefixing Elasticsearch indices), and
`make <service> sandbox ISOLATED=1` starts and migrates it. The remaining reasons
for container mode are unchanged.

**Revised 2026-09-13: one execution mode, not two.** The original design offered a
native-process mode alongside the container mode, on the grounds that a rebuild loop
is too slow to iterate in. Measured, a warm rebuild is ~19s against ~1s for a
reloader — the speed argument was sound, but the conclusion was not: it assumed the
source lives on the developer's laptop, and that assumption is what forced off-host
execution.

Bind-mounting the host checkout into the sandbox container gets both properties —
~1s reload *and* container networking — so the second mode buys nothing. The
container mode is now the only documented path, and the native mode survives only as
an escape hatch for anyone who cannot put source on the host.

The saving is not just one less code path. Off-host execution is what required
Kafka's external listener, `BIND_ADDRESS=0.0.0.0` across Postgres/Redis/ImmuDB/
Elasticsearch/OTLP, and the gateway being able to dial back into a laptop. With
sandboxes local to the host, only the gateway port has to leave it.

What the mount does *not* cover: the venv sits outside it, so a shared library, a new
dependency or a Dockerfile change still needs a rebuild (`BAKED=1`), and workers have
no reloader so they restart instead. Compiled services (Go, Java) rebuild regardless
— which is the same mode, just without the reload.

**Option D remains the sane starting point at one or two developers.** Nothing
above forces a sandbox to exist: with no `X-Sandbox` header and an empty
`SANDBOX_ID` everywhere, the baseline serves everything and the isolation machinery
is inert. Build the host first, and reach for sandboxes when collisions actually
hurt.
