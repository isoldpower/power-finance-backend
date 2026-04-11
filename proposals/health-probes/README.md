# Health / Readiness / Liveness Probes

## Why

Kubernetes routes traffic only to pods that pass readiness checks and restarts pods that fail liveness checks. 
Without these endpoints, k8s has no signal — it will send traffic to a pod with a dead DB connection or never 
restart a deadlocked worker.

## Production Concepts Taught

- Difference between **liveness** (process alive?) and **readiness** (process ready to serve traffic?)
- Dependency health aggregation (DB, Redis, RabbitMQ)
- Kubernetes probe configuration (`initialDelaySeconds`, `failureThreshold`, `periodSeconds`)
- Graceful degradation — report degraded state without crashing

## Endpoints to Implement

| Endpoint              | Probe Type | Purpose                                     |
|-----------------------|------------|---------------------------------------------|
| `GET /health/live`    | Liveness   | Process is alive, event loop not deadlocked |
| `GET /health/ready`   | Readiness  | All dependencies reachable                  |
| `GET /health/startup` | Startup    | Migrations ran, app fully initialized       |

## Readiness Check Dependencies

```
PostgreSQL  — execute SELECT 1
Redis       — PING
RabbitMQ    — check connection via pika or kombu
Migrations  — check django_migrations table for unapplied migrations
```

## Response Contract

**Healthy — 200**
```json
{
  "status": "ok",
  "checks": {
    "postgres": "ok",
    "redis": "ok",
    "rabbitmq": "ok"
  }
}
```

**Degraded — 503**
```json
{
  "status": "degraded",
  "checks": {
    "postgres": "ok",
    "redis": "error: connection refused",
    "rabbitmq": "ok"
  }
}
```

## k8s Probe Config (example)

```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 3
```

## Implementation Notes

- Run checks **concurrently** (asyncio or threads) — don't let a slow RabbitMQ check block the postgres check
- Set per-check **timeouts** (1–2s) — a hung check must not hang the probe endpoint
- Liveness must never depend on external services — only whether the process itself is alive
- Cache readiness result for ~1s to avoid hammering DB on every probe tick
- No authentication on health endpoints — k8s probes have no credentials

## Key Blockwalls

- Async probe execution inside sync Django view
- Timeout enforcement per dependency check
- Avoiding false negatives during startup (use startup probe or `initialDelaySeconds`)

## Relevant k8s Docs

- [Configure Liveness, Readiness and Startup Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
