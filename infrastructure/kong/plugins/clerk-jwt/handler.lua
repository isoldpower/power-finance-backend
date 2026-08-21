-- Custom Kong plugin: clerk-jwt
--
-- Validates Clerk-issued session JWTs at the gateway and forwards the
-- caller's identity as `X-User-Id` to upstream services. Clerk uses a
-- rotating RS256 JWKS, so Kong's built-in `jwt` plugin (static keys) is
-- not enough — this plugin fetches the JWKS over HTTP and caches it in
-- Redis (shared across Kong workers and instances).
--
-- Required nginx shared dict (for the single-flight fetch lock only):
--   lua_shared_dict clerk_jwks_locks 1m;
--
-- The JWKS document itself lives in Redis under
-- `{redis_key_prefix}{issuer_url}`. See redis_cache.lua.
--
-- Failure modes return 401 with no body leak; the only thing that crosses
-- the gateway is X-User-Id (sub claim) plus the unchanged Authorization
-- header (kept so downstream services can re-introspect if needed).

local utilities    = require "kong.plugins.clerk-jwt.utilities"
local messages     = require "kong.plugins.clerk-jwt.messages"
local jwks_fetcher = require "kong.plugins.clerk-jwt.fetch_jwks"

local AUTH_HEADER = "Authorization"

-- User preferences live on the Clerk user record in `unsafeMetadata`, which is
-- CLIENT-WRITABLE. Forwarding them as headers off the verified token is what
-- makes them attributable at all; the services still treat the values as
-- untrusted and fall back per field.
local PREFERENCE_HEADERS = {
    { header = "X-User-Currency", claim = "currency" },
    { header = "X-User-Timezone", claim = "timezone" },
    { header = "X-User-Language", claim = "language" },
}


--- Copy the caller's preferences out of the token's `unsafeMetadata`.
--
-- Each header is set or CLEARED unconditionally. Skipping the clear would leave
-- a client-supplied `X-User-Currency` intact whenever the preference is unset which is unlikely.
local forward_preferences = function(payload)
    local metadata = payload and payload.unsafeMetadata or {}

    for _, preference in ipairs(PREFERENCE_HEADERS) do
        local value = metadata[preference.claim]
        if type(value) == "string" and value ~= "" then
            kong.service.request.set_header(preference.header, value)
        else
            kong.service.request.clear_header(preference.header)
        end
    end
end

-- PRIORITY 801 is deliberately below Kong's bundled rate-limiting plugin
-- (priority 901). The IP-floor rate limit must fire before clerk-jwt so
-- that attackers can't burn JWT verification CPU by spraying invalid
-- tokens at the gateway — they hit the IP cap and get 429'd first.
local ClerkJwtHandler = {
    PRIORITY = 801,
    VERSION  = "0.2.0",
}


function ClerkJwtHandler:access(config)
    local auth_header = kong.request.get_header(AUTH_HEADER)
    local token = utilities.extract_bearer(auth_header)
    if not token then
        kong.log.info("clerk-jwt: no token found attached")
        return messages.no_token_response()
    end

    local unverified_jwt = utilities.load_unverified_jwt(token)
    if not unverified_jwt then
        return messages.wrong_jwt_received()
    end

    local kid = utilities.get_kid_from_jwt(unverified_jwt)
    if not kid then
        return messages.wrong_jwt_received()
    end

    local related_jwk, resolve_error = jwks_fetcher.resolve_jwk_for_kid(config, kid)
    if resolve_error then
        kong.log.err("clerk-jwt: ", resolve_error)
        return messages.jwks_retrieve_failed()
    end
    if not related_jwk then
        return messages.no_matching_jwks()
    end

    local encoded_pem, encode_error = utilities.encode_jwk_as_pem(related_jwk)
    if not encoded_pem then
        kong.log.err("clerk-jwt pem encoder: ", encode_error)
        return messages.failed_key_pem_encoding()
    end

    local verified_jwt = utilities.get_verified_jwt(encoded_pem, unverified_jwt, {
        issuer_url          = config.issuer_url,
        clock_skew_seconds  = config.clock_skew_seconds,
    })
    if not verified_jwt then
        return messages.invalid_jwt_token()
    end

    if not utilities.check_authorized_party(verified_jwt, config.allowed_azp_parties) then
        kong.log.warn("clerk-jwt: azp claim mismatch")
        return messages.invalid_azp()
    end

    local sub_claim = verified_jwt.payload and verified_jwt.payload.sub
    if not sub_claim or sub_claim == "" then
        return messages.missing_sub_claim()
    end

    kong.ctx.shared.clerk_claims = verified_jwt.payload
    kong.service.request.set_header("X-User-Id", sub_claim)
    forward_preferences(verified_jwt.payload)
end


return ClerkJwtHandler
