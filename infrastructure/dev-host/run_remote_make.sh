#!/usr/bin/env bash
set -euo pipefail

# Run on a developer laptop. Anything that touches the baseline's Redis — the sandbox
# routes — has to run where the baseline runs. This is that single ssh hop, with the
# laptop-side defaults already filled in, shared by every `*-remote` target.
usage="usage: run_remote_make.sh <dev-host> <remote-user> <repo-path> <make-target> [VAR=value]..."
dev_host="${1:?$usage}"
remote_user="${2:-}"
repo_path="${3:?missing repo path on the dev host}"
make_target="${4:?missing make target}"
shift 4

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
    echo "On the machine the baseline runs on, run 'make ${make_target}' directly." >&2
    exit 1
fi

# The repo path goes in unquoted so a leading ~ expands in the remote shell; every
# argument is quoted, because a sandbox name or target is likelier to carry a surprise.
arguments=""
for assignment in "$@"; do
    name="${assignment%%=*}"
    value="${assignment#*=}"
    arguments+=$(printf ' %s=%q' "$name" "$value")
done

remote_command="cd ${repo_path} && make ${make_target}${arguments}"

echo "on $ssh_target: make ${make_target}${arguments}"
exec ssh "$ssh_target" "$remote_command"
