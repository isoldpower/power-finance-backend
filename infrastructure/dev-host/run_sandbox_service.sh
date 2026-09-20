#!/usr/bin/env bash
# See ../../README.md → "Shared dev environment"
set -uo pipefail

usage="usage: run_sandbox_service.sh <sandbox-env-file> <service-env-file|-> <required-vars> <label=command>..."
sandbox_env_file="${1:?$usage}"
service_env_file="${2:?$usage}"
required_variables="${3:?$usage}"
shift 3

if [ "$#" -eq 0 ]; then
    echo "$usage" >&2
    exit 1
fi

if [ ! -f "$sandbox_env_file" ]; then
    echo "No sandbox environment at $sandbox_env_file." >&2
    echo "Write one first:" >&2
    echo "  make sandbox-env NAME=<sandbox> SERVICE=<service> DEV_HOST=localhost" >&2
    exit 1
fi

set -a
if [ "$service_env_file" != "-" ] && [ -f "$service_env_file" ]; then
    # shellcheck disable=SC1090
    . "$service_env_file"
fi
# shellcheck disable=SC1090
. "$sandbox_env_file"
set +a

missing=()
for variable in $required_variables; do
    [ -z "${!variable:-}" ] && missing+=("$variable")
done

if [ "${#missing[@]}" -gt 0 ]; then
    echo "Missing required environment: ${missing[*]}" >&2
    echo "" >&2
    echo "Endpoints come from $sandbox_env_file (rewrite it with 'make sandbox-env')." >&2
    if [ "$service_env_file" != "-" ]; then
        echo "Service-owned settings come from $service_env_file — copy its .env.example." >&2
    fi
    exit 1
fi

file_isolation="${SANDBOX_ISOLATED:-0}"
if [ -n "${ISOLATED:-}" ] && [ "$file_isolation" != "1" ]; then
    echo "ISOLATED=1 was asked for, but $sandbox_env_file points at the shared baseline." >&2
    echo "Rewrite it first:" >&2
    echo "  make sandbox-env NAME=<sandbox> SERVICE=<service> DEV_HOST=<host> ISOLATED=1" >&2
    exit 1
fi
if [ -z "${ISOLATED:-}" ] && [ "$file_isolation" = "1" ]; then
    echo "warning: $sandbox_env_file is an isolated environment, but ISOLATED=1 was not" >&2
    echo "         passed, so this laptop's sandbox Postgres has not been started." >&2
    echo "         Start it with: make sandbox-datastores NAME=${SANDBOX_ID:-<sandbox>}" >&2
fi

if [ -z "${SANDBOX_ID:-}" ]; then
    echo "warning: SANDBOX_ID is empty, so this runs as the baseline: its consumers" >&2
    echo "         will take untagged traffic and compete with the dev host's own." >&2
fi

pids=()
labels=()

# macOS ships bash 3.2: no `wait -n`, no associative arrays, and killing the
# subshell that owns a pipeline leaves the real process (uvicorn, the consumer)
# orphaned. So: parallel arrays, a polling supervisor, and a recursive kill.
kill_tree() {
    local parent="$1"
    local child
    for child in $(pgrep -P "$parent" 2>/dev/null); do
        kill_tree "$child"
    done
    kill "$parent" 2>/dev/null
}

stop_everything() {
    trap - INT TERM EXIT
    local index=0
    while [ "$index" -lt "${#pids[@]}" ]; do
        kill_tree "${pids[$index]}"
        index=$((index + 1))
    done
    wait 2>/dev/null
}

trap stop_everything INT TERM EXIT

for process in "$@"; do
    label="${process%%=*}"
    command_line="${process#*=}"

    ( eval "$command_line" 2>&1 | sed "s/^/[${label}] /" ) &
    pids+=("$!")
    labels+=("$label")
    echo "started ${label}: ${command_line}"
done

echo "sandbox '${SANDBOX_ID:-baseline}' running ${#pids[@]} process(es) — Ctrl-C stops all"

while :; do
    index=0
    while [ "$index" -lt "${#pids[@]}" ]; do
        if ! kill -0 "${pids[$index]}" 2>/dev/null; then
            echo "${labels[$index]} exited — stopping the rest" >&2
            exit 1
        fi
        index=$((index + 1))
    done
    sleep 1
done
