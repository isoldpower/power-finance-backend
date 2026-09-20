#!/usr/bin/env bash
# See ./README.md → "Scripts here"
set -euo pipefail

usage="usage: run_remote_make.sh <dev-host> <remote-user> <repo-path> <make-target> [VAR=value]..."
dev_host="${1:?$usage}"
remote_user="${2:-}"
repo_path="${3:?missing repo path on the dev host}"
make_target="${4:?missing make target}"
shift 4

ssh_target="$dev_host"
if [ -n "$remote_user" ]; then
    ssh_target="${remote_user}@${dev_host}"
fi

if [ "$dev_host" = "localhost" ] || [ "$dev_host" = "127.0.0.1" ]; then
    echo "DEV_HOST is '$dev_host' — pass the dev host's tailnet name, e.g. DEV_HOST=pf-dev-host" >&2
    echo "On the machine the baseline runs on, run 'make ${make_target}' directly." >&2
    exit 1
fi

arguments=""
for assignment in "$@"; do
    name="${assignment%%=*}"
    value="${assignment#*=}"
    arguments+=$(printf ' %s=%q' "$name" "$value")
done

remote_command="cd ${repo_path} && make ${make_target}${arguments}"

echo "on $ssh_target: make ${make_target}${arguments}"
exec ssh "$ssh_target" "$remote_command"
