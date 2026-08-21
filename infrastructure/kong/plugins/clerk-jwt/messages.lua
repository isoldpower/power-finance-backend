-- Centralised 401 response builders.
--
-- Each helper calls `kong.response.exit`, which terminates the
-- request immediately — callers should `return messages.X()` so the
-- access phase short-circuits cleanly without further processing.
--
-- Every one of them answers in the API's standard error envelope with
-- `error.code = "unauthorized"`: a client parses a gateway failure exactly
-- the way it parses a service failure.
--
-- Messages are intentionally generic; they avoid leaking internal
-- failure reasons (token shape, JWKS state, key id) to the caller, while
-- staying specific enough in the gateway log to debug from.

local envelope = require "power_finance.envelope"


local function unauthorized(message)
    return envelope.exit(401, "unauthorized", message)
end


--- 401 for a request that did not carry a usable bearer token.
-- Triggered when the `Authorization` header is missing, empty, or does
-- not match the `Bearer <token>` pattern.
local no_token_response = function()
    return unauthorized("Missing or malformed Authorization header.")
end


--- 401 when JWKS could not be obtained.
-- The cache was empty and the upstream JWKS fetch failed (transport
-- error, non-200, or malformed body). Usually transient.
local jwks_retrieve_failed = function()
    return unauthorized("Could not verify the token: identity provider is unreachable.")
end


--- 401 for a structurally invalid JWT.
-- The bearer string was present but did not parse as a valid JWT, or it
-- lacked the required `kid` header.
local wrong_jwt_received = function()
    return unauthorized("Token is malformed.")
end


--- 401 when the token's `kid` is not in the JWKS document.
-- Returned only after a refetch, so the kid is genuinely unknown to the issuer.
local no_matching_jwks = function()
    return unauthorized("Token was signed with an unrecognised key.")
end


--- 401 for a JWK that could not be converted to a PEM.
-- The JWK was structurally valid but failed PEM encoding (corrupt key
-- material, unsupported `kty`). Internal from the caller's perspective.
local failed_key_pem_encoding = function()
    return unauthorized("Could not verify the token.")
end


--- 401 when signature or claim verification fails.
-- Bad signature, expired token, wrong issuer.
local invalid_jwt_token = function()
    return unauthorized("Token is invalid or expired.")
end


--- 401 for a verified JWT missing the `sub` claim.
-- Without `sub` there is no identity to forward downstream.
local missing_sub_claim = function()
    return unauthorized("Token carries no subject claim.")
end


--- 401 when `azp` is not in the configured allow-list.
-- Only emitted if `allowed_azp_parties` is set; binds tokens to a
-- specific frontend origin.
local invalid_azp = function()
    return unauthorized("Token was not issued for an allowed client.")
end


local exports = {
    no_token_response       = no_token_response,
    jwks_retrieve_failed    = jwks_retrieve_failed,
    wrong_jwt_received      = wrong_jwt_received,
    no_matching_jwks        = no_matching_jwks,
    failed_key_pem_encoding = failed_key_pem_encoding,
    invalid_jwt_token       = invalid_jwt_token,
    missing_sub_claim       = missing_sub_claim,
    invalid_azp             = invalid_azp,
}

return exports
