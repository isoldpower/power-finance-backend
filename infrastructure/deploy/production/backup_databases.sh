#!/usr/bin/env bash
# See ./README.md → "Backups"
set -euo pipefail

repository_directory="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$repository_directory"

set -a
. ./.env
set +a

backup_directory="${BACKUP_DIRECTORY:-$HOME/backups/power-finance}"
retention_days="${BACKUP_RETENTION_DAYS:-14}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
compose=(docker compose --env-file .env -p pf-production
    -f compose.yaml -f infrastructure/deploy/compose.baseline.yaml -f infrastructure/deploy/production/compose.production.yaml)
database_services=(postgres-write postgres-read postgres-ai webhook-postgres)

export PRODUCTION_IMAGE_TAG="${PRODUCTION_IMAGE_TAG:-unused-by-backup}"

mkdir -p "$backup_directory"

for service_name in "${database_services[@]}"; do
    dump_path="$backup_directory/$service_name-$timestamp.dump"
    echo "==> $service_name → $dump_path"
    "${compose[@]}" exec -T "$service_name" \
        sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' \
        > "$dump_path.partial"
    mv "$dump_path.partial" "$dump_path"
done

find "$backup_directory" -name '*.dump' -mtime "+$retention_days" -delete
find "$backup_directory" -name '*.partial' -delete

if [ -n "${BACKUP_RCLONE_DESTINATION:-}" ]; then
    echo "==> sync → $BACKUP_RCLONE_DESTINATION"
    rclone sync "$backup_directory" "$BACKUP_RCLONE_DESTINATION" --include '*.dump'
fi

echo "backup $timestamp done"
