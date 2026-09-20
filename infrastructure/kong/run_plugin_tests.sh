#!/usr/bin/env bash
# See ../README.md → "Kong gateway / Plugin tests"
set -euo pipefail

image="${KONG_IMAGE:-kong:3.7}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

status=0
for spec in "$repo_root"/infrastructure/kong/plugins/*/__tests__/*_spec.lua; do
    [ -e "$spec" ] || continue
    plugin_dir="$(cd "$(dirname "$spec")/.." && pwd)"
    echo "== $(basename "$(dirname "$plugin_dir")")/$(basename "$plugin_dir") $(basename "$spec")"
    docker run --rm \
        -v "$plugin_dir:/p:ro" \
        -e PLUGIN_DIR=/p \
        --entrypoint /usr/local/openresty/luajit/bin/luajit \
        "$image" "/p/__tests__/$(basename "$spec")" || status=1
done

exit "$status"
