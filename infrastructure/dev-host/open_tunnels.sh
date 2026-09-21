#!/usr/bin/env bash
# See ./README.md → "Scripts here" and "Testing the reverse tunnel"
set -euo pipefail

dev_host="${1:?usage: open_tunnels.sh <dev-host> [local-service-ports] [print-only] [remote-user]}"
local_service_ports="${2:-}"
print_only="${3:-}"
remote_user="${4:-}"

ssh_target="$dev_host"
if [ -n "$remote_user" ]; then
    ssh_target="${remote_user}@${dev_host}"
fi

if [ "$dev_host" = "localhost" ] || [ "$dev_host" = "127.0.0.1" ]; then
    echo "DEV_HOST is '$dev_host' — pass the dev host's tailnet name, e.g. DEV_HOST=pf-dev-host" >&2
    exit 1
fi

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

remote_bind_address="${REMOTE_BIND:-}"
for local_service_port in $local_service_ports; do
    if [ -n "$remote_bind_address" ]; then
        ssh_arguments+=(-R "${remote_bind_address}:${local_service_port}:localhost:${local_service_port}")
    else
        ssh_arguments+=(-R "${local_service_port}:localhost:${local_service_port}")
    fi
done
ssh_arguments+=("$ssh_target")

if [ -n "$print_only" ]; then
    printf 'ssh'
    printf ' %q' "${ssh_arguments[@]}"
    printf '\n'
    exit 0
fi

echo "tunnelling to $ssh_target — Ctrl-C to close"
echo "  outbound: ${forwarded_ports[*]}"
if [ -n "$local_service_ports" ]; then
    if [ -n "$remote_bind_address" ]; then
        echo "  inbound:  $local_service_ports bound on ${remote_bind_address} on the dev host"
    else
        echo "  inbound:  $local_service_ports on the dev host's loopback"
    fi
fi
exec ssh "${ssh_arguments[@]}"
