-- Centralised 401 response builders.
--
-- Each helper calls `kong.response.exit`, which terminates the
-- request immediately — callers should `return messages.X()` so the
-- access phase short-circuits cleanly without further processing.
--
-- Bodies are intentionally generic; they avoid leaking internal
-- failure reasons (token shape, JWKS state, key id) to the caller.


--- 401 response for a request that did not carry a usable bearer token.
-- Triggered when the `Authorization` header is missing, empty, or
-- does not match the `Bearer <token>` pattern.
local no_token_response = function()
    return kong.response.exit(401, {
        message = "Missing or malformed Authorization header.",
    })
end


--- 401 response when JWKS could not be obtained.
-- Indicates the cache was empty and the upstream JWKS fetch failed
-- (transport error, non-200, or malformed body). Usually transient.
local jwks_retrieve_failed = function()
    return kong.response.exit(401, {
        message = "Couldn't retrieve JWKS neither from cache nor from provider. Provider may be unavailable.",
    })
end


--- 401 response for a structurally invalid JWT.
-- The bearer string was present but did not parse as a valid JWT, or
-- it lacked the required `kid` header. Distinct from a verified-but-
-- rejected token (`invalid_jwt_token`).
local wrong_jwt_received = function()
    return kong.response.exit(401, {
        message = "Received invalid JWT after retrieve. The issue may be related to internal state mismatch.",
    })
end


--- 401 response when the token's `kid` is not in the JWKS document.
-- Returned only after a refetch attempt — by this point we have a
-- fresh JWKS and the kid is genuinely unknown to the issuer.
local no_matching_jwks = function()
    return kong.response.exit(401, {
        message = "No matching JWKS key for retrieve token kid.",
    })
end


--- 401 response for a JWK that could not be converted to a PEM.
-- Indicates the JWK fetched from the issuer was structurally valid
-- but failed PEM encoding (corrupt key material, unsupported `kty`).
-- Treated as an internal error from the caller's perspective.
local failed_key_pem_encoding = function()
    return kong.response.exit(401, {
        message = "Retrieving authentication key succeeded but internal PEM-encoder conversion failed. Probably internal error.",
    })
end


--- 401 response when signature or claim verification fails.
-- The JWT parsed and a matching key was found, but `verify_jwt_obj`
-- rejected it: bad signature, expired token, wrong issuer, etc.
local invalid_jwt_token = function()
    return kong.response.exit(401, {
        message = "JWT token verification failed. Invalid or malformed JWT token received.",
    })
end


--- 401 response for a verified JWT missing the `sub` claim.
-- Without `sub` we cannot populate the `X-User-Id` header that
-- upstream services depend on, so the request is rejected.
local missing_sub_claim = function()
    return kong.response.exit(401, {
        message = "JWT missing `sub` claim which is supposed to be present as a unique resource identifier. Consult with provider docs for message structure.",
    })
end


--- 401 response when `azp` is not in the configured allow-list.
-- Only emitted if `allowed_azp_parties` is set on the plugin
-- instance; binds tokens to a specific frontend origin.
local invalid_azp = function()
    return kong.response.exit(401, {
        message = "JWT `azp` claim does not match any allowed authorized party.",
    })
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
