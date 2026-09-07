# Custom plugins

Five in-tree Kong plugins. What each one does at the pipeline level, and how the
two rate-limit tiers interact, is in [../../README.md](../../README.md) → "Kong
gateway"; this file is the per-plugin detail — why each exists as custom Lua at
all, and why it sits where it does in the chain.

They are copied into the image at build time, one directory per plugin under
`/usr/local/share/lua/5.1/kong/plugins/`, and enabled through `KONG_PLUGINS`.

## Priority chain

Kong runs access-phase plugins from highest priority to lowest. The order here
is not cosmetic: each plugin below `clerk-jwt` reads the verified claims that
`clerk-jwt` stashes in `kong.ctx.shared.clerk_claims`, so it has to run after
it.

| priority | plugin | why there |
| --- | --- | --- |
| 901 | `rate-limiting` (bundled) | the IP floor runs before JWT verification, so spraying invalid tokens hits the cap rather than burning verification CPU |
| 801 | `clerk-jwt` | deliberately below the IP floor, above everything that needs claims |
| 700 | `read-at-least` | needs `clerk_claims` |
| 700 | `write-ral-version` | mirrors `read-at-least` so the pair sits at the same relative position |
| 650 | `read-fallback` | below both, so `X-User-Id` and the resolved `Read-At-Least` are already on the request it forwards |
| 600 | `user-tier-rate-limit` | needs `clerk_claims` |

## clerk-jwt

Validates Clerk-issued session JWTs and forwards the caller's identity as
`X-User-Id`.

Custom because Clerk uses a **rotating RS256 JWKS**, and Kong's bundled `jwt`
plugin only takes static keys. This one fetches the JWKS over HTTP and caches it
in Redis under `{redis_key_prefix}{issuer_url}` (see `clerk-jwt/redis_cache.lua`),
shared across Kong workers and instances. The single-flight fetch lock is the
one thing that needs node-local memory rather than Redis, so it uses an nginx
shared dict:

    lua_shared_dict clerk_jwks_locks 1m;

which the image sets via `KONG_NGINX_HTTP_LUA_SHARED_DICT`.

Failure modes return 401 with no body leak. The only things that cross the
gateway are `X-User-Id` (the `sub` claim) and the unchanged `Authorization`
header, kept so a downstream service can re-introspect if it needs to.

User preferences (`X-User-Currency`, `X-User-Timezone`, `X-User-Language`) are
forwarded off the same verified token. They live on the Clerk user record in
`unsafeMetadata`, which is **client-writable** — forwarding them off the token
is what makes them attributable at all. Services still treat the values as
untrusted and fall back per field.

## read-at-least

The request half of the Read-At-Least header. The response half — signing
`X-Write-Version` on write routes and recording the per-user offset — is
`write-ral-version`, kept separate so the two can attach to their own routes
without cross-coupling.

- When the client **supplies** a `Read-At-Least` header, it is validated as
  `<offset>:<hex-hmac-sha256>` against a gateway-internal secret. This is what
  stops a client forging an arbitrary offset to force Read Service 507
  fallbacks.
- When the client **omits** it, the user's latest write offset is looked up in
  Redis (`ral:user:{sub}`, populated by `write-ral-version`) and a freshly
  signed header is injected. Falls **open** — no header, free read — on a Redis
  miss or any lookup failure.

"Offset" here is the Postgres outbox seq id (`BIGSERIAL`), not the Kafka offset.
See `write-ral-version/redis_writer.lua` for how the value gets into Redis.

## write-ral-version

The response-side counterpart to `read-at-least`, attached to write routes. It
runs across two phases, and the split is forced by OpenResty:

- **`header_filter`** — reads the raw outbox seq the Write Service emitted in
  `X-Write-Version`, HMAC-signs it, and rewrites the header in place so the
  client sees `{seq}:{hex-hmac-sha256}`: exactly the shape it must send back as
  `Read-At-Least`. HMAC is CPU-only, so it is safe in this phase.
- **`log`** — best-effort writes `(user_id, seq)` to `gateway-redis` under
  `ral:user:{sub}` through a monotonic Lua script, so the gateway can inject a
  default header for that user's later reads. The Redis call cannot live in
  `header_filter`: OpenResty forbids cosocket APIs (TCP, Redis, HTTP) there and
  throws *"API disabled in the context of header_filter_by_lua"*. The `log`
  phase runs after the response is fully sent and explicitly supports cosockets.

The point of all of it is that Write Service stays ignorant of the HMAC secret,
of the Redis side-channel, and of the `Read-At-Least` wire format. It just
returns the `BIGSERIAL` outbox row id as a plain integer.

## read-fallback

Transparent read-your-writes fallback, attached to the Read Service route.

It proxies each read itself, and when Read Service answers `fallback_status`
(507 — its projection is behind the client's `Read-At-Least`) it re-issues the
request against the Write Service's always-consistent fallback-read endpoint and
returns that instead. The client sees one response and never the 507.

Self-proxying in the access phase is the only way to do this: it is the one
phase that both sees the upstream status and still permits an HTTP call.

## user-tier-rate-limit

The per-user ceiling that sits on top of the bundled IP floor. No claims means
an anonymous request, and the plugin is a no-op — the IP floor still applies.

Custom because Kong's bundled `rate-limiting` plugin allows only **one instance
per scope**, and two tiers are needed at once: the IP floor and the per-user
ceiling. A second tier therefore has to be a separate plugin class.

Counting uses a **sliding window** — two buckets per window in Redis, the
previous one weighted by the fraction of it the window still covers — so a
caller cannot spend a full allowance either side of a boundary and get twice the
limit in two seconds. The check and the increment run as one Redis script
(`window_script.lua`), so concurrent requests cannot both read a count below the
limit and both pass, and a rejected request spends no budget. `Retry-After` is
computed from when the estimate decays back under the limit, usually well before
the next boundary. Failure modes are fail-open.
