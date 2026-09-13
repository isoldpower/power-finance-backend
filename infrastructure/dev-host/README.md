# Dev host

What turns a MacBook M2 Pro (16 GB) into the shared dev host. Run these on the
**server**, not on a developer laptop.

## Order

1. **Put the repo outside `~/Documents`.** That directory is TCC-protected: a
   process spawned by a daemon (`sshd`, `tailscaled`, `launchd`) **hangs rather
   than errors** when it reads from there, and Full Disk Access is granted
   per-binary, never per-user. `~/srv/power-finance-backend` is a fine home.

2. **Docker runtime — colima**, not Docker Desktop (no GUI login on a headless
   box):

   ```bash
   brew install colima docker docker-compose
   colima start --cpu 8 --memory 12 --disk 80 --vm-type vz --mount-type virtiofs
   ```

   12 GB for the VM leaves macOS ~4 GB. The tuned baseline needs about 9 GB of
   limits and draws closer to 5 GB idle.

3. **Survive reboot.** `restart: unless-stopped` restarts *containers*, not the
   VM, so colima itself needs launchd:

   ```bash
   cp infrastructure/dev-host/com.powerfinance.colima.plist ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/com.powerfinance.colima.plist
   ```

   The host must also be set to log in automatically, or a LaunchAgent never
   runs after a power cycle. `sudo systemsetup -setrestartpowerfailure on` is
   worth setting too.

4. **Tailscale** on the host and on every laptop:

   ```bash
   brew install --cask tailscale
   sudo tailscale up --hostname pf-dev-host
   ```

   Take the tailnet name from `tailscale status`. That is `DEV_HOST` below.

5. **Point the stack at the tailnet and start it:**

   ```bash
   # .env on the dev host
   BIND_ADDRESS=0.0.0.0          # see the port table — 8080 is the one that matters
   ADMIN_BIND_ADDRESS=127.0.0.1  # Kong admin, Jaeger UI, Flink UI stay local
   KAFKA_EXTERNAL_HOST=pf-dev-host
   OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317

   make baseline-up
   ```

6. **Give developers a way to edit the checkout here** — VS Code Remote SSH or
   JetBrains Gateway against this host, or a branch they push and you pull. Their
   sandbox mounts this working tree, so this is where the code has to be.

## The colima trap

**Publishing to a specific host IP does not work under colima.** Docker binds
inside colima's Linux VM, which has no Tailscale interface, so
`BIND_ADDRESS=100.x.y.z` fails with *"cannot assign requested address"*. Use
`0.0.0.0` and let colima forward from every macOS interface. The same applies to
any VM-backed Docker on macOS.

Because `0.0.0.0` means *every* interface, the tailnet is not a firewall on its
own: keep `ADMIN_BIND_ADDRESS=127.0.0.1` so Kong's unauthenticated admin API
(full gateway config control), the Jaeger UI and the Flink UI are not published,
and reach them through an SSH tunnel when you need them.

## What each port is for

Sandboxes run **on this host** with the developer's source bind-mounted, so the
only port a developer strictly needs is the gateway. Everything below it is for
convenience (psql, a REPL) or for the off-host escape hatch.

| Port | Service | Who needs it |
| --- | --- | --- |
| 8080 | Kong proxy | **every developer — the only required one** |
| 5433 / 5434 / 5436 / 5437 | write / read / ai / webhook Postgres | `psql` from a laptop; off-host escape hatch |
| 9200 | Elasticsearch | queries from a laptop; escape hatch |
| 19092 | Kafka external listener | escape hatch only |
| 6383 / 6384 | write / read Redis | escape hatch only |
| 3322 | ImmuDB | escape hatch only |
| 4317 / 4318 | Jaeger OTLP ingest | escape hatch only |
| 8001 | Kong admin | **local only** |
| 16686 | Jaeger UI | local only, or tunnel |
| 8085 | Flink UI | local only, or tunnel |

Because sandboxes are local to the host, `BIND_ADDRESS` can stay `127.0.0.1` and
only the gateway need be published to the tailnet. Widen it only for the ports you
actually want to reach from a laptop — the escape-hatch rows are not needed for
normal work.

`KAFKA_EXTERNAL_HOST` must be the name the laptop uses, because a Kafka client
reconnects to whatever the broker *advertises*, not to the address it dialled.
Set it wrong and metadata succeeds while every fetch fails.

## Scripts here

| Script | Purpose |
| --- | --- |
| `generate_sandbox_env.sh` | Escape hatch only: writes the env file that points a natively-run service at the baseline. Driven by `make sandbox-env`. |
| `prune_sandbox_routes.sh` | Drops gateway routes whose sandbox container is gone. Driven by `make sandbox-prune`. |
| `com.powerfinance.colima.plist` | LaunchAgent that starts colima at login. |

## Routes are ephemeral

`gateway-redis` runs with persistence off on purpose — Kong's rate-limit counters
are disposable. Sandbox routes live in the same Redis, so **restarting
`gateway-redis` drops every sandbox route**. Re-register with `make sandbox-up`
(or `make sandbox-route`); routes also carry a 7-day TTL so forgotten ones expire.
