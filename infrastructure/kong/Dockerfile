# See ../README.md → "Kong gateway / Custom image"
# Build context: ./infrastructure/kong
FROM kong:3.7

# --- lua-resty-jwt (required by the clerk-jwt plugin) ---
USER root
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && git clone --depth=1 --recurse-submodules https://github.com/cdbattags/lua-resty-jwt.git /tmp/lua-resty-jwt \
    && cd /tmp/lua-resty-jwt \
    && luarocks make lua-resty-jwt-dev-0.rockspec \
    && rm -rf /tmp/lua-resty-jwt

# --- Bake the declarative config + custom plugins into the image ---
# (deploy-ready: no bind mounts needed; only secrets/ports come from runtime env)
COPY kong.yml /etc/kong/kong.yml
COPY plugins/clerk-jwt            /usr/local/share/lua/5.1/kong/plugins/clerk-jwt
COPY plugins/read-at-least        /usr/local/share/lua/5.1/kong/plugins/read-at-least
COPY plugins/write-ral-version    /usr/local/share/lua/5.1/kong/plugins/write-ral-version
COPY plugins/user-tier-rate-limit /usr/local/share/lua/5.1/kong/plugins/user-tier-rate-limit
COPY plugins/read-fallback        /usr/local/share/lua/5.1/kong/plugins/read-fallback

# --- Static configuration (non-secret) baked so the image runs standalone ---
ENV KONG_DATABASE=off \
    KONG_DECLARATIVE_CONFIG=/etc/kong/kong.yml \
    KONG_PLUGINS=bundled,clerk-jwt,read-at-least,write-ral-version,user-tier-rate-limit,read-fallback \
    KONG_PROXY_ACCESS_LOG=/dev/stdout \
    KONG_ADMIN_ACCESS_LOG=/dev/stdout \
    KONG_PROXY_ERROR_LOG=/dev/stderr \
    KONG_ADMIN_ERROR_LOG=/dev/stderr \
    KONG_ADMIN_LISTEN=0.0.0.0:8001 \
    KONG_PROXY_LISTEN="0.0.0.0:8000 http2, 0.0.0.0:8443 http2 ssl" \
    KONG_NGINX_PROXY_PROXY_BUFFERING=off \
    KONG_NGINX_PROXY_PROXY_READ_TIMEOUT=3600s \
    KONG_NGINX_PROXY_PROXY_SEND_TIMEOUT=3600s \
    KONG_NGINX_HTTP_LUA_SHARED_DICT="clerk_jwks_locks 1m"

USER kong

EXPOSE 8000 8001 8443

HEALTHCHECK --interval=10s --timeout=5s --retries=5 CMD kong health

LABEL org.opencontainers.image.source=https://github.com/isoldpower/power-finance-backend \
      org.opencontainers.image.title="power-finance/api-gateway" \
      org.opencontainers.image.description="Kong gateway with Clerk JWT auth, read-at-least, and tiered rate-limit plugins."
