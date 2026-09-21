#!/usr/bin/env bash
# See ./README.md → "Scripts here"
set -euo pipefail

route_key_prefix="${1:?usage: prune_sandbox_routes.sh <redis-key-prefix> <baseline-project>}"
baseline_project="${2:?missing baseline project}"

redis_command() {
    docker compose -p "$baseline_project" exec -T gateway-redis redis-cli "$@"
}

live_addresses=$(
    docker ps --filter "name=${baseline_project%-baseline}-sbx-" --format '{{.Names}}' 2>/dev/null |
        while read -r container_name; do
            docker inspect "$container_name" \
                --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' 2>/dev/null
        done
)

pruned_count=0
kept_count=0
while read -r route_key; do
    [ -z "$route_key" ] && continue
    sandbox_name="${route_key#"$route_key_prefix"}"
    target=$(redis_command GET "$route_key" | tr -d '\r')
    target_host="${target%%:*}"

    if printf '%s\n' "$live_addresses" | grep -qx "$target_host"; then
        kept_count=$((kept_count + 1))
        continue
    fi

    if ! printf '%s' "$target_host" | grep -qE '^[0-9]+(\.[0-9]+){3}$'; then
        echo "keeping '$sandbox_name' -> $target (off-host target, cannot verify)"
        kept_count=$((kept_count + 1))
        continue
    fi

    redis_command DEL "$route_key" >/dev/null
    echo "pruned '$sandbox_name' -> $target (no live container)"
    pruned_count=$((pruned_count + 1))
done < <(redis_command --scan --pattern "${route_key_prefix}*" | tr -d '\r')

echo "pruned $pruned_count, kept $kept_count"
