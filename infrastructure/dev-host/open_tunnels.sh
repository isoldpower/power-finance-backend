#!/usr/bin/env bash
set -euo pipefail

# Run on a developer laptop. Forwards the baseline's infrastructure to localhost so
# a natively-run service reaches it, and optionally forwards a local port back so
# the gateway can route to that service. Nothing on the dev host has to be
# published beyond the gateway for this to work.
dev_host="${1:?usage: open_tunnels.sh <dev-host> [local-service-port] [print-only] [remote-user]}"
local_service_port="${2:-}"
print_only="${3:-}"
remote_user="${4:-}"

# The account on the dev host is rarely the account on the laptop, and ssh defaults
# to the local one. Tailscale SSH rejects that with "tailnet policy does not permit
# you to SSH as user <you>", which reads like an ACL problem but is usually just the
# wrong username.
ssh_target="$dev_host"
if [ -n "$remote_user" ]; then
    ssh_target="${remote_user}@${dev_host}"
fi

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

# The reverse forward binds on the dev host's loopback by default. That is enough when
# the container runtime can reach the host's loopback (Docker Desktop can). If it
# cannot, bind it on all of the host's interfaces instead — which additionally needs
# "GatewayPorts clientspecified" in the host's sshd_config.
remote_bind_address="${REMOTE_BIND:-}"
if [ -n "$local_service_port" ]; then
    if [ -n "$remote_bind_address" ]; then
        ssh_arguments+=(-R "${remote_bind_address}:${local_service_port}:localhost:${local_service_port}")
    else
        ssh_arguments+=(-R "${local_service_port}:localhost:${local_service_port}")
    fi
fi
ssh_arguments+=("$ssh_target")

if [ -n "$print_only" ]; then
    printf 'ssh'
    printf ' %q' "${ssh_arguments[@]}"
    printf '\n'
    exit 0
fi

echo "tunnelling to $ssh_target — Ctrl-C to close"
echo "  outbound: ${forwarded_ports[*]}"
if [ -n "$local_service_port" ]; then
    if [ -n "$remote_bind_address" ]; then
        echo "  inbound:  $local_service_port bound on ${remote_bind_address} on the dev host"
    else
        echo "  inbound:  $local_service_port on the dev host's loopback"
    fi
fi
exec ssh "${ssh_arguments[@]}"
