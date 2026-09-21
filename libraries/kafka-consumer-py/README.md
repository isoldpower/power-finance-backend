# kafka-consumer-py

The async Kafka consumer runtime shared by the Python services: outbox-envelope
decoding, event routing, effect execution plans, health-guarded handlers and
SIGTERM-aware consume loops.

## Message context and sandbox isolation

This library never imports OpenTelemetry. `message_context/` declares two
structural ports and ships inert defaults:

| Port | Contract | Default |
|---|---|---|
| `MessageContextBinder` | `bind(headers)` / `unbind(token)` / `read_sandbox_id(headers)` | `NullMessageContextBinder` — no-ops, reads no sandbox |
| `SandboxTrafficPolicy` | `own_sandbox_id`, `is_owned_traffic(id)` | `PermissiveSandboxTrafficPolicy` — accepts everything |

`observability-py` satisfies both structurally (`KafkaMessageContextBinder`,
`SandboxTrafficMatcher`) without either library importing the other. A service
wires them in:

```python
from observability import build_kafka_message_context_components

message_context = build_kafka_message_context_components()
consumer_loop = build_consumer_loop(
    config=config,
    router=router,
    context_binder=message_context.context_binder,
    traffic_policy=message_context.traffic_policy,
    ...,
)
```

Pass nothing and the library behaves exactly as it did before tracing existed.

### How the decorators compose

`build_consumer_loop` (and `KafkaConsumerRunner`) wrap the routed processor:

```
ContextBoundMessageProcessor      binds trace context for the record, always unbinds
└── SandboxFilteredMessageProcessor   drops records owned by another sandbox
    └── RoutedMessageProcessor        decodes and dispatches
```

Context is bound outermost so that a skip is still logged inside the producer's
trace.

### Consumer groups are not optional

A sandbox consumer **must** run under its own group, or it joins the baseline's
group and steals its partitions — the baseline then silently loses messages.
`resolve_sandbox_scoped_group_id(group_id, sandbox_id)` returns
`"<group>-sbx-<sandbox>"` for a sandbox and the group unchanged for the baseline.
Apply it wherever a `ConsumerConfig` is built, and use the same scoped value for
the dedupe store — dedupe rows are keyed by consumer group, so an unscoped store
lets one side mark the other's messages as already consumed.

Filtering does not repartition, so per-user ordering survives it.

## Tests

```bash
uv run pytest libraries/kafka-consumer-py -q
```
