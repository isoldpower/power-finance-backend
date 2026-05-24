local jwt   = require "resty.jwt"
local pkey  = require "resty.openssl.pkey"
local cjson = require "cjson.safe"


--- Extract the bearer token from an `Authorization` header value.
-- Accepts the canonical `Bearer <token>` form, case-insensitive on
-- the scheme. Anything else (missing header, wrong scheme, no token
-- body) yields nil so the caller can fail fast with a 401.
--
-- @param auth_header string|nil  raw `Authorization` header value
-- @return string|nil  the opaque token portion, or nil if absent / malformed
local extract_bearer = function(auth_header)
    if not auth_header or auth_header == "" then
        return nil
    end

    local prefix, token = auth_header:match("^(%a+)%s+(.+)$")
    if not prefix or prefix:lower() ~= "bearer" then
        return nil
    end

    return token
end


--- Parse a JWT string into a resty.jwt object without verifying its
-- signature. Used to read the `kid` header so the caller can pick
-- the right JWKS entry before the (expensive) signature verify pass.
-- Returns nil for any garbage that does not decode as a valid JWT.
--
-- @param jwt_token string  the raw JWT compact-serialized string
-- @return table|nil  resty.jwt object (header / payload / signature), or nil
local load_unverified_jwt = function(jwt_token)
    local unverified_jwt = jwt:load_jwt(jwt_token)
    if not unverified_jwt or not unverified_jwt.valid then
        return nil
    end

    return unverified_jwt
end


--- Read the `kid` (key id) claim from a JWT header. Clerk always sets
-- this for session tokens; absence indicates a malformed token and
-- callers should reject rather than guessing a key.
--
-- @param unverified_jwt table  object produced by `load_unverified_jwt`
-- @return string|nil  the `kid` header value, or nil if missing
local get_kid_from_jwt = function(unverified_jwt)
    return unverified_jwt.header and unverified_jwt.header.kid
end


--- Look up a JWK entry inside a JWKS document by its `kid`.
--
-- Clerk always issues with a kid header. Missing kid is malformed; we
-- refuse rather than guessing the first JWKS entry (which would
-- silently mask schema bugs in multi-key responses).
--
-- @param jwks table  decoded JWKS document with a `keys` array
-- @param kid string|nil  key id from the unverified JWT header
-- @return table|nil  the matching JWK dict, or nil if no entry matches
local find_key_for_kid = function(jwks, kid)
    if not kid then
        return nil
    end
    if not jwks or type(jwks.keys) ~= "table" or #jwks.keys == 0 then
        return nil
    end

    for _, key in ipairs(jwks.keys) do
        if key.kid == kid then
            return key
        end
    end

    return nil
end


--- Convert a JWK dict into a PEM-encoded public key suitable for
-- `resty.jwt:verify_jwt_obj`.
--
-- lua-resty-openssl.pkey.new takes the JWK dict as a JSON-encoded
-- string under `format = "JWK"`. The dict must keep the canonical
-- JWK keys (kty, n, e) — passing a hand-built table with a
-- different schema silently produces a key that fails verification.
--
-- @param jwk_keys table  single JWK dict as returned by the issuer
-- @return string|nil  PEM-encoded public key on success
-- @return string|nil  human-readable error message on failure
local encode_jwk_as_pem = function(jwk_keys)
    local encoded_jwk, encode_error = cjson.encode(jwk_keys)
    if not encoded_jwk then
        return nil, "JWK JSON encode failed: " .. (encode_error or "Unknown Error")
    end

    local key, pkey_error = pkey.new(encoded_jwk, {
        format = "JWK"
    })
    if not key then
        return nil, "JWK to PKey encode process: " .. (pkey_error or "Unknown Error")
    end

    local pem, pem_error = key:to_PEM("public")
    if not pem then
        return nil, "PKey to PEM encode process: " .. (pem_error or "Unknown Error")
    end

    return pem, nil
end


--- Verify a previously parsed JWT against a PEM public key.
--
-- Always requires the `exp` claim. When `options.issuer_url` is set
-- the `iss` claim must match exactly. When `options.clock_skew_seconds`
-- is a positive number it is forwarded as `lifetime_grace_period`,
-- absorbing minor clock drift between the issuer and Kong.
--
-- @param pem_token string  PEM-encoded public key from `encode_jwk_as_pem`
-- @param unverified_jwt table  object produced by `load_unverified_jwt`
-- @param options table|nil  optional verification config:
--   * issuer_url string         expected `iss` claim value
--   * clock_skew_seconds number tolerance window for `exp`
-- @return table|nil  resty.jwt object with `verified = true` on success
local get_verified_jwt = function(pem_token, unverified_jwt, options)
    local verify_options = { require_exp_claim = true }
    if options then
        if options.issuer_url then
            verify_options.valid_issuers = { options.issuer_url }
        end
        if options.clock_skew_seconds and options.clock_skew_seconds > 0 then
            verify_options.lifetime_grace_period = options.clock_skew_seconds
        end
    end

    local verified_jwt = jwt:verify_jwt_obj(pem_token, unverified_jwt, verify_options)
    if not verified_jwt or not verified_jwt.verified then
        local reason = verified_jwt and verified_jwt.reason or "JWT signature mismatch"
        kong.log.warn("clerk-jwt: verification failed: ", reason)
        return nil
    end

    return verified_jwt
end


--- Check the `azp` (authorized party) claim against an allow-list.
--
-- An empty or nil allow-list disables the check (returns true). With
-- a non-empty list, the token's `azp` must exactly match one entry —
-- this binds tokens to a specific frontend origin and prevents a
-- token issued for another Clerk app on the same issuer from being
-- accepted by this gateway.
--
-- @param verified_jwt table  resty.jwt object from `get_verified_jwt`
-- @param allowed_azp_parties table|nil  array of allowed `azp` values
-- @return boolean  true if check passes (or is disabled), false on mismatch
local check_authorized_party = function(verified_jwt, allowed_azp_parties)
    if not allowed_azp_parties or #allowed_azp_parties == 0 then
        return true
    end

    local azp = verified_jwt.payload and verified_jwt.payload.azp
    if not azp then
        return false
    end

    for _, allowed in ipairs(allowed_azp_parties) do
        if azp == allowed then
            return true
        end
    end

    return false
end


local exports = {
    extract_bearer         = extract_bearer,
    load_unverified_jwt    = load_unverified_jwt,
    get_kid_from_jwt       = get_kid_from_jwt,
    find_key_for_kid       = find_key_for_kid,
    encode_jwk_as_pem      = encode_jwk_as_pem,
    get_verified_jwt       = get_verified_jwt,
    check_authorized_party = check_authorized_party,
}

return exports
