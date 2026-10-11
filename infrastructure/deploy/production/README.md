# Production (three VMs)

The backend on three Oracle Cloud Always Free **Ampere A1** VMs (arm64) in one
VCN, behind a **Cloudflare Tunnel**. GitHub Actions builds the images and every VM
pulls them from GHCR.

```
browser ─https─▶ Cloudflare ─tunnel─▶ core VM ─────────────────────────────────────────────┐
         manage-api.powerfinance.site  cloudflared ▶ Kong ▶ write / read / ai / push / webhook │
                                       Postgres ×4, Redis ×3, ImmuDB, Kafka, Debezium, Jaeger │
                                            │ :9200 https                ▲ :19092 Kafka     │
                                            ▼                            │ :4317 OTLP       │
                                       search VM                     stream VM              │
                                       Elasticsearch + Kibana        Flink jobmanager +     │
                                                                     taskmanager (antifraud)│
```

| VM | Role | Shape | Boot volume | Compose files |
| --- | --- | --- | --- | --- |
| `pf-core` | `core` | 2 OCPU, 12 GB | 100 GB | `compose.yaml` + `infrastructure/deploy/compose.baseline.yaml` + `infrastructure/deploy/production/compose.production.yaml` |
| `pf-search` | `search` | 1 OCPU, 6 GB | 50 GB | `services/read-service/compose.elastic.yaml` + `infrastructure/deploy/production/compose.production-search.yaml` |
| `pf-stream` | `stream` | 1 OCPU, 6 GB | 50 GB | `infrastructure/deploy/production/compose.production-stream.yaml` |

Together the three VMs use exactly the free A1 allowance (4 OCPU, 24 GB) and all
200 GB of free block storage.
Each VM keeps its role in `.env` as `PRODUCTION_ROLE`, and every `make prod-*`
target picks the compose files for that role.

**What crosses VMs** (private IPs only; the network security groups allow these and nothing else):

| From → to | Port | What | Protection |
| --- | --- | --- | --- |
| core → search | 9200 | read-service, read-write-consumer, read-es-init → Elasticsearch | TLS (cert issued for the search VM's FQDN) + `elastic` password |
| stream → core | 19092 | Flink → Kafka `EXTERNAL` listener (advertises the core FQDN) | plaintext, no auth: rely on the `nsg-core` rule |
| stream → core | 4317 | Flink OTel agent → Jaeger OTLP gRPC | plaintext |

Everything else stays on each VM's loopback: Kong admin, Jaeger UI, Kibana, the
Flink UI, and the databases. `make prod-tunnel` brings those UIs to your laptop.

| File | Role |
| --- | --- |
| `infrastructure/deploy/production/compose.production.yaml` | Core overlay: images pinned to the commit SHA, Django `settings.production`, ES on the search VM with its CA mounted, Flink disabled, Kafka `:19092` and OTLP `:4317` published on the private IP, `cloudflared` |
| `infrastructure/deploy/production/compose.production-search.yaml` | ES heap 2 GB, port 9200 on the private IP, Kibana on loopback |
| `infrastructure/deploy/production/compose.production-stream.yaml` | Standalone Flink cluster pointed at the core VM |
| `{core,search,stream}.env.example` | What each VM's `.env` needs |
| `bootstrap_host.sh <role>` | One-time VM setup: Docker, log rotation, `vm.max_map_count`, swap (except search), unattended upgrades, backup timer (core) |
| `check_environment.sh` | Per role: refuses empty secrets and dev defaults; on core, also refuses to start without the ES CA |
| `backup_databases.sh` + `power-finance-backup.{service,timer}` | Nightly `pg_dump` on core, optional `rclone` off-site copy |
| `.github/workflows/publish-images.yaml` | Builds the 7 images natively on `ubuntu-24.04-arm` for each push to `main`, tagged `<full sha>` and `latest` |

## 0. Oracle Cloud

1. **Optional: upgrade to Pay-As-You-Go** (Billing → Upgrade). It costs $0 inside
   the Always Free limits. It exempts the VMs from idle reclaim, and A1 is less
   often "Out of capacity". Plain Always Free works too. Oracle reclaims an A1
   instance only when CPU (p95), network **and memory** all stay under 20% for 7
   days. Elasticsearch's locked heap and Flink's JVMs keep memory above that, but
   check with `free -m` on each VM after the first deploy. Set a $1 budget alert
   either way.
2. **VCN**: create it with the wizard (*VCN with Internet Connectivity*). Keep
   **DNS labels** on, so each VM gets a private FQDN
   `<hostname>.<subnet-label>.<vcn-label>.oraclevcn.com`.
3. **Default security list** of the public subnet: delete the ingress rule
   `0.0.0.0/0 TCP 22`. Security lists and NSGs are combined, so if that rule stays,
   SSH stays open to the whole internet whatever the NSGs say. Keep the egress rule
   and the ICMP rules.
4. **Network security groups** (VCN → Network Security Groups), with the default
   egress rule to all destinations, and these ingress rules:

   | NSG | Source | Port | For |
   | --- | --- | --- | --- |
   | `nsg-core` | your IP `/32` | TCP 22 | SSH |
   | `nsg-core` | NSG `nsg-stream` | TCP 19092, 4317 | Flink → Kafka, OTLP |
   | `nsg-search` | your IP `/32` | TCP 22 | SSH |
   | `nsg-search` | NSG `nsg-core` | TCP 9200 | core → Elasticsearch |
   | `nsg-stream` | your IP `/32` | TCP 22 | SSH |

   Docker-published ports bypass the host firewall, so these NSGs are the real
   firewall. The cross-VM ports are also bound to private IPs only.
5. **Instances** (Compute → Instances → Create), ×3 from the table above:
   - Image: **Canonical Ubuntu 24.04** (aarch64). Shape **VM.Standard.A1.Flex**.
   - Hostname: `pf-core` / `pf-search` / `pf-stream`. Public subnet with a public
     IPv4, so each VM can pull images and you can SSH in. Attach its NSG. Paste
     your SSH key.
   - If you hit "Out of capacity", try another availability domain or retry later.
6. On your laptop, add SSH aliases so the Make targets can reach each VM:

   ```
   # ~/.ssh/config
   Host pf-core
       HostName <core public IP>
       User ubuntu
   Host pf-search
       HostName <search public IP>
       User ubuntu
   Host pf-stream
       HostName <stream public IP>
       User ubuntu
   ```

## 1. Bootstrap each VM

```bash
ssh pf-core          # then pf-search, pf-stream
git clone https://github.com/isoldpower/power-finance-backend.git ~/power-finance-backend
cd ~/power-finance-backend
infrastructure/deploy/production/bootstrap_host.sh core     # search / stream on the others
exit                 # log back in so the docker group applies
```

`hostname -I` prints the private IP and `hostname -f` the private FQDN. You need
both in the next step.

## 2. Configure each VM

On each VM: `cp infrastructure/deploy/production/<role>.env.example .env && chmod 600 .env`,
fill it in (`openssl rand -hex 32` for each secret), then run `make prod-check`.

- **search**: set `ELASTIC_PASSWORD` and `ELASTICSEARCH_CERTIFICATE_HOSTNAME` (its
  own FQDN) **before the first start**. The password is baked into the data volume
  and the TLS certificate is issued once.
- **core**: `DEMO_TOKEN_SECRET` (at least 32 characters) signs the portfolio's guest demo tokens; write-service and Kong both read it.
  `ELASTIC_PASSWORD` must match the search VM's. `KAFKA_EXTERNAL_HOST` is
  core's own FQDN, `CORE_PRIVATE_ADDRESS` core's own IP, `SEARCH_PRIVATE_HOSTNAME`
  the search FQDN. Database and ImmuDB passwords are baked into volumes on first
  start too.
- **stream**: only `CORE_PRIVATE_HOSTNAME`.

**Clerk:** create a *production* instance for `powerfinance.site` and add its DNS
records in Cloudflare. `CLERK_ISSUER_URL` is the instance's Frontend API URL
(`https://clerk.powerfinance.site`).

### Cloudflare Tunnel (core)

1. Zero Trust → **Networks → Tunnels → Create a tunnel → Cloudflared**, name it
   `power-finance-production`.
2. Copy the token (the string after `--token`) into core's `CLOUDFLARE_TUNNEL_TOKEN`.
   Skip installing the connector: the `cloudflared` container is the connector.
3. **Public hostname**: `manage-api` . `powerfinance.site` → service **HTTP**
   `api-gateway:8000`.
4. SSL/TLS → Edge Certificates: **Always Use HTTPS** on, minimum TLS 1.2.

SSE (`/api/v1/notifications/stream`) and the assistant WebSocket (`/api/v1/chat`)
pass through the tunnel. Cloudflare drops connections idle for 100 s. The push
service's 15 s heartbeat keeps the stream alive.

### GHCR access

Container packages are private by default, even for a public repository. Either
make each `power-finance/*` package **Public** (Package settings → Change
visibility), or run `docker login ghcr.io -u isoldpower` with a `read:packages`
PAT on core and stream. The search VM pulls only Elastic images, so it needs
neither.

## 3. First deploy

The order matters: core needs Elasticsearch's CA, and Flink needs Kafka.

```bash
ssh pf-search 'cd ~/power-finance-backend && make prod-deploy'   # ES generates its CA + cert
make prod-copy-es-ca                                             # laptop: search CA → core .secrets/
ssh pf-core   'cd ~/power-finance-backend && make prod-deploy'
ssh pf-stream 'cd ~/power-finance-backend && make prod-deploy'
```

Before that, the image workflow must be green for the commit you deploy: merge to
`main`, or run **Actions → Publish images → Run workflow**.

## Deploying updates

```bash
make prod-deploy-all              # laptop: search → core → stream, each at origin/main
make prod-deploy-all REF=<sha>    # a specific commit, e.g. a rollback
```

Images are tagged with the full commit SHA, and `make prod-up` uses `git rev-parse
HEAD`. So on every VM the checked-out config (Kong, connectors, Postgres config)
and the images come from the same commit. If CI hasn't finished for that commit,
`docker compose pull` fails before anything restarts. Migrations are not reversed
on rollback.

## Operations

| | |
| --- | --- |
| Logs | on a VM: `make prod-logs SERVICE=write-service` (omit `SERVICE` for all) |
| Admin UIs | laptop: `make prod-tunnel`, then Kong admin `localhost:8001`, Jaeger `localhost:16686`, Kibana `localhost:5601` (user `elastic`), Flink `localhost:8085` |
| Disk | `docker system df`; `docker image prune -a --filter until=168h` after a few deploys |
| Connectivity | from core: `curl --cacert .secrets/elasticsearch-ca.crt -u elastic https://<search FQDN>:9200`; from stream: `nc -vz <core FQDN> 19092` |

If a cross-VM port is unreachable even though the NSG allows it, check
the Oracle Ubuntu image's own iptables (`sudo iptables -L FORWARD -n`). Docker's
chains must come before the image's final `REJECT`.

## Backups

On core, `power-finance-backup.timer` runs `backup_databases.sh` nightly at 03:30
UTC. It writes `pg_dump --format=custom` files for postgres-write, postgres-read,
postgres-ai and webhook-postgres to `~/backups/power-finance`, keeps
`BACKUP_RETENTION_DAYS` days, and optionally syncs them off the VM.

**Off-site (OCI Object Storage, 20 GB free):**

1. Storage → Buckets → create a **private** bucket `power-finance-backups`.
2. Profile → **Customer Secret Keys** → generate one (an S3-compatible access key
   and secret).
3. On core, run `rclone config` and create remote `oci`: type `s3`, provider
   `Other`, endpoint
   `https://<namespace>.compat.objectstorage.<region>.oraclecloud.com`.
4. `BACKUP_RCLONE_DESTINATION=oci:power-finance-backups` in core's `.env`.
5. `make prod-backup` once by hand, then `systemctl list-timers power-finance-backup*`.

Restore one database:

```bash
docker compose ... exec -T postgres-write pg_restore -U postgres -d power_finance_write --clean --if-exists < dump
```

**Not covered:** ImmuDB (the ledger, on core) and Elasticsearch (search).
Elasticsearch is a projection and can be rebuilt. ImmuDB can't, so plan a volume
backup for core (OCI block volume backups: 5 are free).
