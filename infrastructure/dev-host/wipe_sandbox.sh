#!/usr/bin/env bash
# See ./README.md → "Scripts here"
set -euo pipefail

usage="usage: wipe_sandbox.sh <sandbox-name> <route-key-prefix> <baseline-project> <sandbox-project> [force]"
sandbox_name="${1:?$usage}"
route_key_prefix="${2:?$usage}"
baseline_project="${3:?$usage}"
sandbox_project="${4:?$usage}"
force="${5:-}"

baseline_compose() {
    docker compose -p "$baseline_project" "$@"
}

group_suffix="-sbx-${sandbox_name}"

kafka_groups() {
    baseline_compose exec -T kafka \
        kafka-consumer-groups --bootstrap-server localhost:9092 --list 2>/dev/null |
        tr -d '\r' | grep -- "${group_suffix}$" || true
}

report_pending() {
    local group="$1"
    local pending
    pending=$(
        baseline_compose exec -T kafka \
            kafka-consumer-groups --bootstrap-server localhost:9092 \
            --describe --group "$group" 2>/dev/null |
            tr -d '\r' | awk '$6 ~ /^[0-9]+$/ && $6 > 0 { total += $6 } END { print total + 0 }'
    )
    echo "${pending:-0}"
}

groups=$(kafka_groups)

if [ -n "$groups" ]; then
    undrained=""
    for group in $groups; do
        pending=$(report_pending "$group")
        if [ "$pending" != "0" ]; then
            undrained+="  $group — $pending event(s) never applied by anyone"$'\n'
        fi
    done

    if [ -n "$undrained" ] && [ -z "$force" ]; then
        echo "Refusing to wipe '$sandbox_name': these groups still have unapplied events." >&2
        printf '%s' "$undrained" >&2
        echo "" >&2
        echo "Baseline consumers skipped those events and have already committed past" >&2
        echo "them, so deleting the groups now loses them. Run the sandbox's consumers" >&2
        echo "until they drain, or re-run with FORCE=1 to accept the gap." >&2
        exit 1
    fi
fi

echo "== containers"
SANDBOX_ID="$sandbox_name" BASELINE_NETWORK_NAME="${baseline_project}_default" \
    docker compose -p "$sandbox_project" -f compose.sandbox.yaml \
    down --remove-orphans --volumes 2>&1 | sed 's/^/   /' || true

echo "== gateway routes"
route_keys=$(baseline_compose exec -T gateway-redis redis-cli --scan --pattern "${route_key_prefix}${sandbox_name}:*" | tr -d '\r')
if [ -z "$route_keys" ]; then
    echo "   none"
else
    for key in $route_keys; do
        baseline_compose exec -T gateway-redis redis-cli DEL "$key" < /dev/null >/dev/null
        echo "   dropped ${key#"$route_key_prefix"}"
    done
fi

echo "== consumer groups"
if [ -z "$groups" ]; then
    echo "   none"
else
    for group in $groups; do
        baseline_compose exec -T kafka \
            kafka-consumer-groups --bootstrap-server localhost:9092 \
            --delete --group "$group" >/dev/null 2>&1 &&
            echo "   deleted $group" ||
            echo "   could not delete $group (is a consumer still connected?)" >&2
    done
fi

echo ""
echo "sandbox '$sandbox_name' wiped — X-Sandbox: $sandbox_name now behaves like no header at all."
echo "Processes running on a laptop are not covered: stop those yourself."
