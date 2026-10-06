#!/usr/bin/env bash
# See ./README.md → "2. Configure each VM"
set -euo pipefail

environment_file="${1:-.env}"

if [ ! -f "$environment_file" ]; then
    echo "$environment_file not found — copy infrastructure/deploy/production/<role>.env.example to .env and fill it in."
    exit 1
fi

set -a
. "$environment_file"
set +a

case "${PRODUCTION_ROLE:-}" in
    core)
        required_variables=(
            CORE_PRIVATE_ADDRESS KAFKA_EXTERNAL_HOST SEARCH_PRIVATE_HOSTNAME
            CLOUDFLARE_TUNNEL_TOKEN CLERK_ISSUER_URL READ_AT_LEAST_HMAC_SECRET
            WRITE_SERVICE_SECRET_KEY READ_SERVICE_SECRET_KEY
            WRITE_DATABASE_PASSWORD READ_DATABASE_PASSWORD AI_DATABASE_PASSWORD WEBHOOK_DATABASE_PASSWORD
            IMMUDB_PASSWORD ELASTIC_PASSWORD
        )
        ;;
    search)
        required_variables=(SEARCH_PRIVATE_ADDRESS ELASTICSEARCH_CERTIFICATE_HOSTNAME ELASTIC_PASSWORD KIBANA_PASSWORD)
        ;;
    stream)
        required_variables=(CORE_PRIVATE_HOSTNAME)
        ;;
    *)
        echo "PRODUCTION_ROLE must be core, search or stream (got '${PRODUCTION_ROLE:-}')"
        exit 1
        ;;
esac
known_default_values=(postgres immudb changeme dev-only-secret-key-change-me)

problems=()
for variable_name in "${required_variables[@]}"; do
    value="${!variable_name:-}"
    if [ -z "$value" ]; then
        problems+=("$variable_name is empty")
        continue
    fi
    for default_value in "${known_default_values[@]}"; do
        [ "$value" = "$default_value" ] && problems+=("$variable_name is still the dev default '$default_value'")
    done
done

if [ "$PRODUCTION_ROLE" = core ]; then
    if [ "${#READ_AT_LEAST_HMAC_SECRET}" -lt 32 ]; then
        problems+=("READ_AT_LEAST_HMAC_SECRET must be at least 32 characters")
    fi
    certificate_authority_file="${ELASTICSEARCH_CA_CERTIFICATE_FILE:-./.secrets/elasticsearch-ca.crt}"
    if [ ! -s "$certificate_authority_file" ]; then
        problems+=("$certificate_authority_file is missing — run \`make prod-copy-es-ca\` from your laptop once the search VM is up")
    fi
    case "${CLERK_ISSUER_URL:-}" in
        *.clerk.accounts.dev*) echo "  ! CLERK_ISSUER_URL points at a Clerk development instance" ;;
    esac
fi

if [ "${#problems[@]}" -gt 0 ]; then
    printf '  ✗ %s\n' "${problems[@]}"
    exit 1
fi

echo "environment OK ($PRODUCTION_ROLE)"
