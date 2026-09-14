#!/usr/bin/env bash
set -euo pipefail

# Run on a developer laptop. Sandbox routes live in the baseline's Redis, which runs
# on the dev host, so registering one means running `make sandbox-route` over there.
# This is that single ssh hop, with the laptop-side defaults already filled in.
dev_host="${1:?usage: register_remote_route.sh <dev-host> <remote-user> <repo-path> <sandbox-name> <service> <target>}"
remote_user="${2:-}"
repo_path="${3:?missing repo path on the dev host}"
sandbox_name="${4:?missing sandbox name}"
service="${5:?missing service}"
target="${6:?missing target}"

# The account on the dev host is rarely the account on the laptop, and ssh defaults
# to the latter. Tailscale SSH rejects that with "tailnet policy does not permit you
# to SSH as user <you>", which reads like an ACL problem but is usually just the
# wrong username.
ssh_target="$dev_host"
if [ -n "$remote_user" ]; then
    ssh_target="${remote_user}@${dev_host}"
fi

if [ "$dev_host" = "localhost" ] || [ "$dev_host" = "127.0.0.1" ]; then
    echo "DEV_HOST is '$dev_host' — pass the dev host's tailnet name, e.g. DEV_HOST=pf-dev-host" >&2
    echo "On the machine the baseline runs on, register routes with plain 'make sandbox-route'." >&2
    exit 1
fi

# The repo path goes in unquoted so a leading ~ expands in the remote shell; the rest
# is quoted, because a sandbox name or target is far likelier to carry a surprise.
remote_command="cd ${repo_path} && $(printf 'make sandbox-route NAME=%q SERVICE=%q TARGET=%q' \
    "$sandbox_name" "$service" "$target")"

echo "registering on $ssh_target: sandbox '$sandbox_name' $service -> $target"
exec ssh "$ssh_target" "$remote_command"
