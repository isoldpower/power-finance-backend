#!/usr/bin/env bash
set -euo pipefail

# Run on a developer laptop. Forwards the baseline's infrastructure to localhost so
# a natively-run service reaches it, and optionally forwards a local port back so
# the gateway can route to that service. Nothing on the dev host has to be
# published beyond the gateway for this to work.
dev_host="${1:?usage: open_tunnels.sh <dev-host> [local-service-port] [print-only]}"
local_service_port="${2:-}"
print_only="${3:-}"

if [ "$dev_host" = "localhost" ] || [ "$dev_host" = "127.0.0.1" ]; then
    echo "DEV_HOST is '$dev_host' — pass the dev host's tailnet name, e.g. DEV_HOST=pf-dev-host" >&2
    exit 1
fi

# Kafka is forwarded on the port it advertises. The broker advertises
# ${KAFKA_EXTERNAL_HOST}:${KAFKA_EXTERNAL_PORT}, so with KAFKA_EXTERNAL_HOST left
# at localhost a client follows the advertisement straight back into this tunnel.
forwarded_ports=(
    "${KAFKA_EXTERNAL_PORT:-19092}"
    "${WRITE_DATABASE_EXTERNAL_PORT:-5433}"
    "${READ_DATABASE_EXTERNAL_PORT:-5434}"
    "${AI_DATABASE_EXTERNAL_PORT:-5436}"
    "${WEBHOOK_DATABASE_EXTERNAL_PORT:-5437}"
    "${WRITE_REDIS_EXTERNAL_PORT:-6383}"
    "${READ_REDIS_EXTERNAL_PORT:-6384}"
    "${IMMUDB_EXTERNAL_PORT:-3322}"
    "${ELASTICSEARCH_EXTERNAL_PORT:-9200}"
    "${OTLP_GRPC_PORT:-4317}"
    "${OTLP_HTTP_PORT:-4318}"
    "${JAEGER_UI_PORT:-16686}"
)

ssh_arguments=(-N)
for port in "${forwarded_ports[@]}"; do
    ssh_arguments+=(-L "${port}:127.0.0.1:${port}")
done

if [ -n "$local_service_port" ]; then
    ssh_arguments+=(-R "${local_service_port}:localhost:${local_service_port}")
fi
ssh_arguments+=("$dev_host")

if [ -n "$print_only" ]; then
    printf 'ssh'
    printf ' %q' "${ssh_arguments[@]}"
    printf '\n'
    exit 0
fi

echo "tunnelling to $dev_host — Ctrl-C to close"
echo "  outbound: ${forwarded_ports[*]}"
if [ -n "$local_service_port" ]; then
    echo "  inbound:  $local_service_port (gateway can reach your service at host.docker.internal:$local_service_port)"
fi
exec ssh "${ssh_arguments[@]}"
