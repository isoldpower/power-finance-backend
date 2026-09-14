# Dev host

What turns a MacBook M2 Pro (16 GB) into the shared dev host. Run these on the
**server**, not on a developer laptop.

## Order

1. **Put the repo outside `~/Documents`.** That directory is TCC-protected: a
   process spawned by a daemon (`sshd`, `tailscaled`, `launchd`) **hangs rather
   than errors** when it reads from there, and Full Disk Access is granted
   per-binary, never per-user. `~/srv/power-finance-backend` is a fine home.

2. **Docker runtime — colima**, not Docker Desktop (no GUI login on a headless box):

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

5. **Create `.env`. This step is not optional.** Without it the stack still starts —
   Compose falls back to the `${VAR:-default}` defaults — but the two values that
   default to *empty* are exactly the two that break authentication:

   | Variable | No default | Effect when empty |
   | --- | --- | --- |
   | `CLERK_ISSUER_URL` | yes | every request 401s, *"identity provider is unreachable"* |
   | `READ_AT_LEAST_HMAC_SECRET` | yes | read-your-writes silently stops working (needs ≥ 32 chars, and the same value for the `read-at-least` and `write-ral-version` plugins) |

   Everything else — ports, passwords, topics, heap sizes, the OTLP endpoint — has a
   usable default, so a minimal `.env` is genuinely two lines plus whatever you want
   to override:

   ```bash
   cp .env.example .env      # then at minimum:
   CLERK_ISSUER_URL=https://<your-app>.clerk.accounts.dev
   READ_AT_LEAST_HMAC_SECRET=$(openssl rand -hex 32)

   # worth setting on a shared host:
   ELASTICSEARCH_HOSTS=https://es01:9200   # the node this stack starts
   PROXY_BIND_ADDRESS=0.0.0.0              # the gateway — the only port devs need
   BIND_ADDRESS=127.0.0.1                  # datastores stay on loopback
   ADMIN_BIND_ADDRESS=127.0.0.1            # Kong admin, Jaeger UI, Flink UI
   KAFKA_EXTERNAL_HOST=pf-dev-host          # only matters if you widen BIND_ADDRESS
   ```

6. **Start it:**

   ```bash
   make baseline-up
   ```

   **The first run builds seven images and takes 10–20 minutes** — a Gradle build
   for the Flink job, the OpenTelemetry Java agent download, and the Python images.
   Later runs reuse the cache and start in under a minute.

   The `power-finance/*:dev` tags are built locally and exist in no registry, so
   every service that has a `build:` section carries `pull_policy: build`. Without
   it Compose attempts a registry pull first and logs
   `pull access denied … repository does not exist` for each image before falling
   back to building — noisy and slow, but never fatal. If you see those lines, the
   `pull_policy` is missing somewhere.

7. **Give developers SSH access.** They clone and edit on their own machines and
   run the service they are changing there; this host supplies the dependencies.
   `make sandbox-tunnels DEV_HOST=<this host>` on their laptop forwards Kafka,
   the four Postgres instances, Redis, ImmuDB, Elasticsearch, OTLP and the Jaeger
   UI to their localhost, and forwards one local port back so the gateway can route
   to them. Membership of the `docker` group is only needed by whoever runs
   host-side sandboxes; plain SSH is enough for the tunnels.

   Keep a checkout here too, on `main`, for `make baseline-up` — and one per
   developer if anyone uses host-side sandboxes (`make sandbox-up`), since those
   mount whichever tree the command runs in.

## Credentials are baked in at first init

Postgres, ImmuDB and Elasticsearch write their user, password and database/cluster
name into the data directory the **first** time they start, then ignore those
variables forever. Change one in `.env` afterwards and the client uses the new value
against a server that still holds the old one.

Recreating the container does not help — the credential lives in the **volume**.
Either remove the volume and let it re-initialise, or change the password in-place
with SQL.

| Volume | Baked from |
| --- | --- |
| `pf-baseline_postgres_write_data` | `WRITE_DATABASE_{USER,PASSWORD,NAME}` |
| `pf-baseline_postgres_read_data` | `READ_DATABASE_*` |
| `pf-baseline_postgres_ai_data` | `AI_DATABASE_*` |
| `pf-baseline_webhook_postgres_data` | `WEBHOOK_DATABASE_*` |
| `pf-baseline_immudb_data` | `IMMUDB_{USER,PASSWORD}` |
| `pf-baseline_esdata01` | `ELASTIC_PASSWORD`, `CLUSTER_NAME` |

```bash
make baseline-down
docker volume rm pf-baseline_postgres_write_data pf-baseline_postgres_read_data \
                 pf-baseline_postgres_ai_data pf-baseline_webhook_postgres_data
make baseline-up
```

`kafka_data`, `jaeger_data` and `redis_read_data` hold no credentials and can stay.

**Decide these before the first `baseline-up`** and you never meet this. The
database healthchecks now authenticate, so a mismatch shows up as
`postgres-write` going *unhealthy* rather than as a pool timeout inside four
unrelated migrations — but the volume still has to be re-initialised either way.

## When every request 401s

`{"code":"unauthorized","message":"Could not verify the token: identity provider is
unreachable."}` means the gateway could not fetch the JWKS — your token was never
examined. In order of likelihood:

1. **`CLERK_ISSUER_URL` empty or wrong.** It ships empty in `.env.example`. Kong
   resolves it at config load, so recreate the gateway after setting it:
   `docker compose -p pf-baseline -f compose.yaml -f compose.baseline.yaml up -d --force-recreate api-gateway`.
2. **A stale JWKS cache entry** in `gateway-redis` — clear `clerk:jwks:*` keys.
3. **No egress or DNS from the container.** Test on the stack's own network:
   `docker run --rm --network pf-baseline_default curlimages/curl:8.9.1 -s -o /dev/null -w '%{http_code}\n' "$CLERK_ISSUER_URL/.well-known/jwks.json"` — expect 200.
4. **TLS verification** — the fetch uses `ssl_verify = true`, so the image needs CA
   certificates (the custom gateway image installs them).

The plugin logs the real reason, which is always the fastest answer:
`docker logs pf-baseline-api-gateway-1 2>&1 | grep -i clerk-jwt | tail -5`

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

Developers run their service on their own machine and reach everything else through
SSH tunnels (`make sandbox-tunnels`), so the only port that has to be **published**
is the gateway. Everything else is reached over SSH, which is why the gateway has its
own bind address and the rest can stay on loopback.

| Port | Service | Who needs it |
| --- | --- | --- |
| 8080 | Kong proxy | **every developer — the only required one** (`PROXY_BIND_ADDRESS`) |
| 5433 / 5434 / 5436 / 5437 | write / read / ai / webhook Postgres | `psql` from a laptop; off-host escape hatch |
| 9200 | Elasticsearch | queries from a laptop; escape hatch |
| 19092 | Kafka external listener | escape hatch only |
| 6383 / 6384 | write / read Redis | escape hatch only |
| 3322 | ImmuDB | escape hatch only |
| 4317 / 4318 | Jaeger OTLP ingest | escape hatch only |
| 8001 | Kong admin | **local only** |
| 16686 | Jaeger UI | local only, or tunnel |
| 8085 | Flink UI | local only, or tunnel |

The recommended shape is `PROXY_BIND_ADDRESS=0.0.0.0` with
`BIND_ADDRESS=127.0.0.1`: the gateway is reachable over the tailnet, and everything
else is reachable only through an SSH tunnel. Widening `BIND_ADDRESS` is an
alternative to tunnelling, not a requirement — and remember `0.0.0.0` means every
interface, not just the tailnet, so a café network counts.

`KAFKA_EXTERNAL_HOST` interacts with this choice. A Kafka client reconnects to what
the broker advertises, so leave it `localhost` when developers tunnel (the
advertisement points back into their own tunnel) and set it to this host's tailnet
name only if you publish 19092 instead.

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
