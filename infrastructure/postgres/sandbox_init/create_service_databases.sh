#!/usr/bin/env bash
# See ../../dev-host/README.md → "Scripts here"
set -euo pipefail

for database_name in \
    "${WRITE_DATABASE_NAME:-power_finance_write}" \
    "${READ_DATABASE_NAME:-power_finance_read}" \
    "${AI_DATABASE_NAME:-power_finance_ai}" \
    "${WEBHOOK_DATABASE_NAME:-power_finance_webhooks}"; do
    existing=$(psql -U "$POSTGRES_USER" -d postgres -tAc \
        "select 1 from pg_database where datname = '${database_name}'")
    if [ "$existing" = "1" ]; then
        echo "database ${database_name} already present"
        continue
    fi
    echo "creating database ${database_name}"
    psql -U "$POSTGRES_USER" -d postgres -c "create database \"${database_name}\""
done
