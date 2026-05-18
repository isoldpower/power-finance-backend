-- Custom Kong plugin: clerk-jwt
--
-- Validates Clerk-issued session JWTs at the gateway and forwards the
-- caller's identity as `X-User-Id` to upstream services. Clerk uses a
-- rotating RS256 JWKS, so Kong's built-in `jwt` plugin (static keys) is
-- not enough — this plugin fetches the JWKS over HTTP and caches it in
-- the shared dict declared in nginx.conf.
--
-- Failure modes return 401 with no body leak; the only thing that crosses
-- the gateway is X-User-Id (sub claim) plus the unchanged Authorization
-- header (kept so downstream services can re-introspect if needed).

local cjson      = require "cjson.safe"
local jwt        = require "resty.jwt"
local http       = require "resty.http"
local pkey       = require "resty.openssl.pkey"

-- PRIORITY 850 is deliberately below Kong's bundled rate-limiting plugin
-- (priority 901). The IP-floor rate limit must fire before clerk-jwt so
-- that attackers can't burn JWT verification CPU by spraying invalid
-- tokens at the gateway — they hit the IP cap and get 429'd first.
local ClerkJwtHandler = {
    PRIORITY = 850,
    VERSION  = "0.2.0",
}

local JWKS_CACHE_NAME = "clerk_jwks_cache"
local JWKS_CACHE_KEY  = "jwks"


local function unauthorized(message)
    return kong.response.exit(401, { message = message })
end


local function fetch_jwks(issuer_url, timeout_ms)
    local httpc = http.new()
    httpc:set_timeout(timeout_ms or 5000)

    local res, err = httpc:request_uri(issuer_url .. "/.well-known/jwks.json", {
        method = "GET",
        ssl_verify = true,
    })
    if not res then
        return nil, "jwks fetch failed: " .. (err or "unknown")
    end
    if res.status ~= 200 then
        return nil, "jwks fetch non-200: " .. tostring(res.status)
    end

    local parsed = cjson.decode(res.body)
    if type(parsed) ~= "table" or type(parsed.keys) ~= "table" then
        return nil, "jwks payload malformed"
    end
    return parsed
end


local function get_jwks(conf)
    local cache = ngx.shared[JWKS_CACHE_NAME]
    if cache then
        local cached = cache:get(JWKS_CACHE_KEY)
        if cached then
            local parsed = cjson.decode(cached)
            if parsed then
                return parsed
            end
        end
    end

    local fresh, err = fetch_jwks(conf.issuer_url, conf.http_timeout_ms)
    if not fresh then
        return nil, err
    end

    if cache then
        cache:set(JWKS_CACHE_KEY, cjson.encode(fresh), conf.jwks_ttl_seconds)
    end
    return fresh
end


local function find_key_for_kid(jwks, kid)
    for _, key in ipairs(jwks.keys) do
        if not kid or key.kid == kid then
            return key
        end
    end
    return nil
end


-- lua-resty-jwt only accepts secrets as PEM-encoded strings for RS256,
-- so we hand off the JWK (n, e) parameters to lua-resty-openssl.pkey,
-- which knows how to construct an RSA public key from JWK and emit PEM.
local function jwk_to_pem(jwk)
    -- lua-resty-openssl.pkey.new takes the JWK dict as a JSON-encoded
    -- string under `format = "JWK"`. The dict must keep the canonical
    -- JWK keys (kty, n, e) — passing a hand-built table with a
    -- different schema silently produces a key that fails verification.
    local key, err = pkey.new(cjson.encode(jwk), { format = "JWK" })
    if not key then
        return nil, "jwk → pkey: " .. (err or "unknown")
    end
    local pem, pem_err = key:to_PEM("public")
    if not pem then
        return nil, "pkey → pem: " .. (pem_err or "unknown")
    end
    return pem
end


local function extract_bearer(auth_header)
    if not auth_header or auth_header == "" then
        return nil
    end
    local prefix, token = auth_header:match("^(%a+)%s+(.+)$")
    if not prefix or prefix:lower() ~= "bearer" then
        return nil
    end
    return token
end


function ClerkJwtHandler:access(conf)
    local auth_header = kong.request.get_header("Authorization")
    local token = extract_bearer(auth_header)
    if not token then
        return unauthorized("Missing or malformed Authorization header.")
    end

    local jwks, err = get_jwks(conf)
    if not jwks then
        kong.log.err("clerk-jwt: ", err)
        return unauthorized("Auth provider unavailable.")
    end

    -- Decode header without verifying to read the `kid`, then look the
    -- matching key up in the JWKS. If the JWT has no kid, fall back to
    -- the first key.
    local unverified = jwt:load_jwt(token)
    if not unverified.valid then
        return unauthorized("Invalid JWT.")
    end
    local kid = unverified.header and unverified.header.kid
    local jwk = find_key_for_kid(jwks, kid)
    if not jwk then
        return unauthorized("No matching JWKS key for token kid.")
    end

    local pem, pem_err = jwk_to_pem(jwk)
    if not pem then
        kong.log.err("clerk-jwt: ", pem_err)
        return unauthorized("Auth key conversion failed.")
    end

    local verified = jwt:verify_jwt_obj(pem, unverified, {
        require_exp_claim = true,
    })
    if not verified or not verified.verified then
        local reason = verified and verified.reason or "signature mismatch"
        kong.log.warn("clerk-jwt: verification failed: ", reason)
        return unauthorized("Invalid or expired JWT.")
    end

    local sub = verified.payload and verified.payload.sub
    if not sub or sub == "" then
        return unauthorized("JWT missing `sub` claim.")
    end

    -- Spec: gateway attaches identity for downstream services to trust.
    kong.service.request.set_header("X-User-Id", sub)

    -- Stash the verified claims for downstream plugins (e.g. read-at-least
    -- reads a default offset claim out of the JWT). Sharing via kong.ctx
    -- avoids a second parse / verify pass.
    kong.ctx.shared.clerk_claims = verified.payload
end


return ClerkJwtHandler
