# See ../README.md → "Kong gateway / Custom image"
FROM kong:3.7

USER root
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && git clone --depth=1 --recurse-submodules https://github.com/cdbattags/lua-resty-jwt.git /tmp/lua-resty-jwt \
    && cd /tmp/lua-resty-jwt \
    && luarocks make lua-resty-jwt-dev-0.rockspec \
    && rm -rf /tmp/lua-resty-jwt
USER kong
