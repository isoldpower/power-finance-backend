#!/usr/bin/env bash
# See ./README.md → "1. Bootstrap the VM"
set -euo pipefail

if [ "$(id -u)" -eq 0 ]; then
    echo "Run as the login user (ubuntu), not root; the script uses sudo itself."
    exit 1
fi

production_role="${1:-}"
case "$production_role" in
    core | search | stream) ;;
    *)
        echo "usage: $0 core|search|stream"
        exit 1
        ;;
esac

repository_directory="$(cd "$(dirname "$0")/../../.." && pwd)"
swap_file_path=/swapfile
swap_size=4G

echo "==> System packages"
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ca-certificates curl git make rclone unattended-upgrades
sudo dpkg-reconfigure -f noninteractive unattended-upgrades

echo "==> Docker Engine + Compose plugin"
if ! command -v docker >/dev/null 2>&1; then
    sudo install -m 0755 -d /etc/apt/keyrings
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
sudo usermod -aG docker "$USER"

echo "==> Docker log rotation"
sudo tee /etc/docker/daemon.json >/dev/null <<'JSON'
{
  "log-driver": "local",
  "log-opts": { "max-size": "20m", "max-file": "5" }
}
JSON
sudo systemctl enable --now docker
sudo systemctl restart docker

echo "==> Kernel settings for Elasticsearch"
echo "vm.max_map_count=262144" | sudo tee /etc/sysctl.d/99-elasticsearch.conf >/dev/null
sudo sysctl --system >/dev/null

if [ "$production_role" = search ]; then
    echo "==> Swap skipped: Elasticsearch locks its heap and must not swap"
else
    echo "==> Swap ($swap_size)"
    if ! swapon --show | grep -q "$swap_file_path"; then
        sudo fallocate -l "$swap_size" "$swap_file_path"
        sudo chmod 600 "$swap_file_path"
        sudo mkswap "$swap_file_path" >/dev/null
        sudo swapon "$swap_file_path"
        echo "$swap_file_path none swap sw 0 0" | sudo tee -a /etc/fstab >/dev/null
    fi
    echo "vm.swappiness=10" | sudo tee /etc/sysctl.d/99-swappiness.conf >/dev/null
    sudo sysctl --system >/dev/null
fi

if [ "$production_role" = core ]; then
    echo "==> Nightly database backup timer"
    sed "s|__REPOSITORY_DIRECTORY__|$repository_directory|g; s|__USER__|$USER|g" \
        "$repository_directory/infrastructure/deploy/production/power-finance-backup.service" \
        | sudo tee /etc/systemd/system/power-finance-backup.service >/dev/null
    sudo cp "$repository_directory/infrastructure/deploy/production/power-finance-backup.timer" \
        /etc/systemd/system/power-finance-backup.timer
    sudo systemctl daemon-reload
    sudo systemctl enable --now power-finance-backup.timer
fi

echo
echo "Done. Log out and back in so the docker group applies, then continue with"
echo "step 2 of infrastructure/deploy/production/README.md."
