# Custom Kong image bundling lua-resty-jwt so the in-tree `clerk-jwt`
# plugin can `require "resty.jwt"` at startup. lua-resty-jwt is not part
# of the upstream kong:3.7 image.
FROM kong:3.7

USER root
# luarocks.org root manifest blows past Lua 5.1's 64KB constant limit and
# fails to load. Install rockspec directly from GitHub so luarocks never
# touches the root manifest. cdbattags is the current upstream maintainer.
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && git clone --depth=1 --recurse-submodules https://github.com/cdbattags/lua-resty-jwt.git /tmp/lua-resty-jwt \
    && cd /tmp/lua-resty-jwt \
    && luarocks make lua-resty-jwt-dev-0.rockspec \
    && rm -rf /tmp/lua-resty-jwt
USER kong
