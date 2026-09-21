# kafka-messages-proto

Protobuf schemas and generated language bindings for cross-service Kafka events.

- **Source of truth:** `protobufs/*.proto`.
- **Generated output:** `generated/<language>/...` — committed so consumers don't
  need `protoc` installed locally. Do not edit by hand.

## Conventions

**Envelope.** Every business event opens with the same three fields —
`event_id` (1), `occurred_at` (2), `schema_version` (3). They are repeated as
flat fields rather than a nested `EventEnvelope` so the JSON wire format stays
flat. `event_id` is the idempotency key consumers dedupe on; `occurred_at` is
when the producer decided the event happened, not when it was published.
`schema_version` is bumped on any breaking change to a concrete payload, and a
consumer that meets a version higher than it understands must route the message
to the DLQ rather than partially process it.

**Field numbering.** 1–3 are the envelope and 4–100 are its headroom. Payload
fields start at 101, and terminal timestamps (`created_at`, `updated_at`,
`deleted_at`, `dispatched_at`) sit at 120+ with the gap below them `reserved`, so
a new field can be added next to its neighbours instead of after the timestamps.
The events predating this rule (`transaction`, `wallet`, `goal`, `user`,
`notification`, `webhook`) open their payload at 10 and cannot be renumbered —
they are already on the wire. New protos use 101+. Field numbers cost nothing
here in any case: the outbox publishes proto JSON, not the binary encoding.

**Partition key.** `events.async` is keyed by the user's external (Clerk) id,
which is what gives per-user ordering and what push-service matches to authorise
an SSE stream. Any event owned by a user therefore carries `user_external_id`
alongside the internal `user_id`; an unowned event is published under the
`"GLOBAL"` key.

**Decimals are strings.** Money never crosses the wire as a float. `amount`,
`balance`, `target`, `zero_balance` and friends are decimal strings.

**Enums.** Values are prefixed with the enum name (`ACCOUNT_GROUP_ASSETS`)
because proto3 scopes them in the enclosing *package*, not the enum — an
unprefixed `ASSETS` would take that name across all of
`power_finance.events.v1`. The zero value never names a real member — it is the
"nobody set this" value, spelled `ACCOUNT_GROUP_WRONG` on the one enum that
exists so far. The outbox encodes with `always_print_fields_with_no_presence=True`,
so an unset enum is indistinguishable on the wire from one explicitly set to its
zero value; giving that slot a meaningful member would make a forgotten field
look like a deliberate answer. Enums serialise as their *name*, upper-case — a
consumer storing lower-case strings owns the fold.

**Deliberate omissions.** There is no `AccountDeleted`: `ai_entries.account_id`
is `ondelete="RESTRICT"` and an account, once seeded for a user, is never
removed. A chart of accounts that could vanish under its own postings would need
a different model, not just an extra event.

**Posting replacement.** A dispatch replaces a transaction's whole leg set
rather than diffing it, and each replacement mints fresh posting ids. The events
of one replacement therefore share a `dispatch_id`, and
`AccountPostingsDispatched` closes the set: it states how many
`AccountPostingDeleted` (`deleted_count`) and `AccountPostingCreated`
(`created_count`) events belong to the dispatch, and carries the dispatch-level
diagnostics (`balanced`, `comment`, `backend`). Counting both sides lets a
consumer verify it saw the whole replacement rather than only its tail: a
dispatch that removes legs without adding any is a real outcome, and one
reporting creates alone would be indistinguishable from a delivery that lost its
deletes. A consumer that applies leg events without waiting for the marker can
render a transaction mid-replacement.

## Regenerating

Run `./generate.sh` (resolves paths relative to itself, runnable from anywhere).
It regenerates Python, Go, and Java bindings:

- **Python** — `--pyi_out` emits `*_pb2.pyi` stubs so mypy can see message
  classes (the `_pb2.py` modules build them dynamically from descriptors, which
  is invisible to static analysis). protoc emits absolute imports rooted at the
  proto path, so the script rewrites them to relative imports to keep the package
  self-contained, then regenerates `__init__.py` re-exports so
  `from kafka_messages import Foo` works without a hand-maintained surface.
- **Go** — `--go_opt=module=<module path>` strips that prefix from each file's
  `go_package`, landing files at `generated/go/events/v1/*.pb.go`. Requires
  `protoc-gen-go` on `PATH`.
- **Java** — `--java_out` uses `protoc`'s built-in Java generator (no plugin).
  The `java_package`/`java_multiple_files`/`java_outer_classname` options on each
  proto land one top-level class per message under
  `generated/java/com/powerfinance/events/v1/`. Consumers add it as a source dir
  plus the `com.google.protobuf:protobuf-java` runtime.

## Packaging

The importable Python package is the generated output: the wheel/editable install
maps `generated/python/kafka_messages` → `kafka_messages` (see `pyproject.toml`).
