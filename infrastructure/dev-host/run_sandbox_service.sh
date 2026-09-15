#!/usr/bin/env bash
set -uo pipefail

# Run on a developer laptop. Starts every process a service is made of — its HTTP
# edge and each of its consumers — against a sandbox's environment, so a routed
# sandbox is never half a service.
#
# The gap this closes: routing read-service to a laptop moves its HTTP edge, but
# its projection consumer is a separate process. Run only the edge and writes stop
# being projected, which surfaces much later as a 507 or as missing data rather
# than as anything pointing at the consumer.
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

# The service's own .env first, the sandbox file second: the sandbox endpoints win,
# which is the precedence the services themselves apply (a real environment variable
# beats a value read from an env file).
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

# Any one of them exiting takes the rest down: a sandbox missing a consumer is the
# failure mode this exists to prevent, so it must not be possible to end up in it
# quietly.
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
