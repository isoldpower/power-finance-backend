#!/usr/bin/env bash
# See ../../README.md → "Quick start"
set -euo pipefail

if [ "$#" -eq 0 ]; then
    echo "usage: $0 <command> [arguments...]"
    exit 2
fi

compose_file="$(cd "$(dirname "$0")" && pwd)/compose.test-datastores.yaml"
compose=(docker compose -f "$compose_file")

running_container_count=$("${compose[@]}" ps --status running --quiet | wc -l | tr -d ' ')

if [ "$running_container_count" -eq 0 ]; then
    "${compose[@]}" up -d --wait --quiet-pull >&2
    trap '"${compose[@]}" down --remove-orphans >/dev/null 2>&1 || true' EXIT
else
    "${compose[@]}" up -d --wait --quiet-pull >/dev/null 2>&1
fi

"$@"
