#!/usr/bin/env bash
set -euo pipefail

sandbox_name="${1:?usage: generate_sandbox_env.sh <sandbox-name> <service> <dev-host> <output-file>}"
service_name="${2:?missing service}"
dev_host="${3:?missing dev host}"
output_file="${4:?missing output file}"

kafka_port="${KAFKA_EXTERNAL_PORT:-19092}"
write_database_port="${WRITE_DATABASE_EXTERNAL_PORT:-5433}"
read_database_port="${READ_DATABASE_EXTERNAL_PORT:-5434}"
ai_database_port="${AI_DATABASE_EXTERNAL_PORT:-5436}"
webhook_database_port="${WEBHOOK_DATABASE_EXTERNAL_PORT:-5437}"
write_redis_port="${WRITE_REDIS_EXTERNAL_PORT:-6383}"
read_redis_port="${READ_REDIS_EXTERNAL_PORT:-6384}"
immudb_port="${IMMUDB_EXTERNAL_PORT:-3322}"
otlp_grpc_port="${OTLP_GRPC_PORT:-4317}"
elasticsearch_port="${ELASTICSEARCH_EXTERNAL_PORT:-9200}"
elasticsearch_hosts="${ELASTICSEARCH_HOSTS:-https://${dev_host}:${elasticsearch_port}}"

# Every other endpoint below is built from "$dev_host", so it follows the tunnel by
# construction. ELASTICSEARCH_HOSTS is the one line a caller can inherit from the
# environment, and an inherited value that names a different host quietly leaves the
# tunnel — reaching the dev host's published port directly, which BIND_ADDRESS keeps
# on its loopback. That failure surfaces much later as a connection error from
# Elasticsearch alone, so say it here.
elasticsearch_note=""
if [ -n "${ELASTICSEARCH_HOSTS:-}" ]; then
    inherited_host=$(printf '%s' "$ELASTICSEARCH_HOSTS" \
        | sed -e 's|^[a-zA-Z][a-zA-Z0-9+.-]*://||' -e 's|[/?#].*$||' -e 's|^.*@||' -e 's|:[0-9]*$||')
    if [ "$inherited_host" != "$dev_host" ]; then
        elasticsearch_note="# Inherited from the environment, NOT built from DEV_HOST=${dev_host} like the lines above.
"
        {
            echo "warning: ELASTICSEARCH_HOSTS is set to '$ELASTICSEARCH_HOSTS'."
            echo "         Every other endpoint points at '$dev_host'; Elasticsearch will not."
            echo "         A laptop should leave it unset — the tunnel then serves it on"
            echo "         https://${dev_host}:${elasticsearch_port}."
        } >&2
    fi
fi

# Credentials are per service in this repo (WRITE_DATABASE_USER, READ_DATABASE_*, …).
# Reading a generic DATABASE_USER/PASSWORD silently falls back to postgres/postgres
# and then fails against any host that set its own passwords.
case "$service_name" in
    write-service|write-*)
        database_port="$write_database_port"
        database_name="${WRITE_DATABASE_NAME:-power_finance_write}"
        database_user="${WRITE_DATABASE_USER:-postgres}"
        database_password="${WRITE_DATABASE_PASSWORD:-postgres}"
        redis_port="$write_redis_port"
        ;;
    read-service|read-*)
        database_port="$read_database_port"
        database_name="${READ_DATABASE_NAME:-power_finance_read}"
        database_user="${READ_DATABASE_USER:-postgres}"
        database_password="${READ_DATABASE_PASSWORD:-postgres}"
        redis_port="$read_redis_port"
        ;;
    ai-service|ai-*)
        database_port="$ai_database_port"
        database_name="${AI_DATABASE_NAME:-power_finance_ai}"
        database_user="${AI_DATABASE_USER:-postgres}"
        database_password="${AI_DATABASE_PASSWORD:-postgres}"
        redis_port="$read_redis_port"
        ;;
    webhook-service)
        database_port="$webhook_database_port"
        database_name="${WEBHOOK_DATABASE_NAME:-power_finance_webhooks}"
        database_user="${WEBHOOK_DATABASE_USER:-postgres}"
        database_password="${WEBHOOK_DATABASE_PASSWORD:-postgres}"
        redis_port="$read_redis_port"
        ;;
    *)
        database_port="$write_database_port"
        database_name="${WRITE_DATABASE_NAME:-power_finance_write}"
        database_user="${WRITE_DATABASE_USER:-postgres}"
        database_password="${WRITE_DATABASE_PASSWORD:-postgres}"
        redis_port="$write_redis_port"
        ;;
esac

# The consumer group a process joins decides who owns a sandbox's events: the baseline
# skips them only when a group named after its own plus this sandbox exists. Pinning
# the group here keeps a locally-run consumer in the same group as the container it
# stands in for, whatever the code defaults say.
case "$service_name" in
    read-service|read-*)
        consumer_group_lines="KAFKA_READ_GROUP_ID=${KAFKA_READ_GROUP_ID:-read-service.write-consumer}
"
        ;;
    ai-service|ai-*)
        consumer_group_lines="KAFKA_AI_GROUP_ID=${KAFKA_AI_GROUP_ID:-ai-service.dispatcher}
"
        ;;
    write-service|write-*)
        consumer_group_lines="KAFKA_AUTOMATION_ENGINE_GROUP_ID=${KAFKA_AUTOMATION_ENGINE_GROUP_ID:-write-service.automation-engine}
KAFKA_FRAUD_ALERTS_GROUP_ID=${KAFKA_FRAUD_ALERTS_GROUP_ID:-write-service.fraud-alerts}
KAFKA_NOTIFICATIONS_INBOUND_GROUP_ID=${KAFKA_NOTIFICATIONS_INBOUND_GROUP_ID:-write-service.notifications-inbound}
"
        ;;
    webhook-service)
        consumer_group_lines="KAFKA_GROUP_ID=${WEBHOOK_KAFKA_GROUP_ID:-webhook-service.deliveries}
"
        ;;
    *)
        consumer_group_lines=""
        ;;
esac

# ai-service and webhook-service read a whole URL rather than DATABASE_* parts.
service_specific_lines=""
case "$service_name" in
    ai-service|ai-*)
        service_specific_lines="AI_DATABASE_URL=postgresql+psycopg://${database_user}:${database_password}@${dev_host}:${database_port}/${database_name}
"
        ;;
    webhook-service)
        service_specific_lines="POSTGRES_DSN=postgres://${database_user}:${database_password}@${dev_host}:${database_port}/${database_name}
"
        ;;
esac

mkdir -p "$(dirname "$output_file")"
cat > "$output_file" <<ENVEOF
# Generated by \`make sandbox-env NAME=$sandbox_name SERVICE=$service_name\`.
# Source this before running $service_name natively against the shared baseline.
# Every endpoint points at the dev host; nothing here starts infrastructure.
SANDBOX_ID=$sandbox_name

KAFKA_BOOTSTRAP_SERVERS=${dev_host}:${kafka_port}
${consumer_group_lines}
DATABASE_HOST=$dev_host
DATABASE_PORT=$database_port
DATABASE_NAME=$database_name
DATABASE_USER=$database_user
DATABASE_PASSWORD=$database_password

REDIS_HOST=$dev_host
REDIS_PORT=$redis_port

IMMUDB_HOST=$dev_host
IMMUDB_PORT=$immudb_port
IMMUDB_USER=${IMMUDB_USER:-immudb}
IMMUDB_PASSWORD=${IMMUDB_PASSWORD:-immudb}

$service_specific_lines
${elasticsearch_note}ELASTICSEARCH_HOSTS=$elasticsearch_hosts
ELASTICSEARCH_USERNAME=${ELASTICSEARCH_USERNAME:-elastic}
ELASTICSEARCH_PASSWORD=${ELASTIC_PASSWORD:-changeme}
ELASTICSEARCH_VERIFY_CERTS=${ELASTICSEARCH_VERIFY_CERTS:-false}

OTEL_EXPORTER_OTLP_ENDPOINT=http://${dev_host}:${otlp_grpc_port}
OTEL_SERVICE_NAME=$service_name
OTEL_DEPLOYMENT_ENVIRONMENT=sandbox
ENVEOF

echo "$output_file"
