#!/usr/bin/env bash
# See ../../README.md → "Giving the baseline back what an isolated sandbox took"
set -euo pipefail

sandbox_name="${1:?usage: replay_sandbox_events.sh <sandbox> <baseline-project> [dry-run] [since] [until]}"
baseline_project="${2:?missing baseline project}"
dry_run="${3:-}"
since="${4:-}"
until_moment="${5:-}"

baseline_compose() {
    docker compose -p "$baseline_project" -f compose.yaml -f compose.baseline.yaml \
        --profile local-elastic "$@"
}

window=()
[ -n "$since" ] && window+=(--since "$since")
[ -n "$until_moment" ] && window+=(--until "$until_moment")

echo "== events carrying sandbox-id=${sandbox_name}"
event_ids=$(baseline_compose exec -T write-service \
    python manage.py replay_sandbox_events --sandbox "$sandbox_name" --list-only \
    "${window[@]+"${window[@]}"}" | tr -d '\r')

if [ -z "$event_ids" ]; then
    echo "   none — nothing to replay"
    exit 0
fi

echo "$event_ids" | sed 's/^/   /'
count=$(printf '%s\n' "$event_ids" | grep -c .)

if [ -n "$dry_run" ]; then
    echo ""
    echo "== read-service dedupe (dry run)"
    printf '%s\n' "$event_ids" | baseline_compose exec -T read-service \
        python manage.py forget_consumed_events --dry-run
    echo ""
    echo "DRY_RUN: would re-publish ${count} event(s). Nothing was changed."
    exit 0
fi

echo ""
echo "== read-service dedupe"
printf '%s\n' "$event_ids" | baseline_compose exec -T read-service \
    python manage.py forget_consumed_events | sed 's/^/   /'

echo ""
echo "== re-publishing"
baseline_compose exec -T write-service \
    python manage.py replay_sandbox_events --sandbox "$sandbox_name" \
    "${window[@]+"${window[@]}"}" | sed 's/^/   /'

echo ""
echo "Elasticsearch is a separate consumer group with its own dedupe and its own"
echo "applied-seq, so it is NOT covered. Rebuild it with:"
echo "  docker compose -p ${baseline_project} exec read-service \\"
echo "      python manage.py backfill_elastic_from_postgres"
