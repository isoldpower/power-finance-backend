-- Centralised error response builders for the read-at-least plugin.
--
-- Each helper calls `kong.response.exit`, which terminates the
-- request immediately — callers should `return messages.X()` so the
-- access phase short-circuits cleanly without further processing.


--- 400 response for a structurally invalid Read-At-Least header.
-- The header was present but did not match the `<offset>:<hex-hmac>`
-- shape. Treated as a client error (bad input), not auth failure.
local malformed_header_message = function()
    return kong.response.exit(400, {
        message = "Received malformed Read-At-Least (RAL) header. Read operation refused.",
    })
end


--- 401 response when HMAC computation fails on the gateway side.
-- Indicates an internal problem signing the offset (e.g. OpenSSL
-- error); from the client's perspective the read cannot proceed.
local header_verification_failure = function()
    return kong.response.exit(401, {
        message = "Read-At-Least (RAL) header verification failed. Couldn't sign received header.",
    })
end


--- 401 response when the client-supplied HMAC does not match.
-- The header parsed and the gateway computed an expected digest, but
-- the signatures differ — either a forged offset or a key mismatch
-- between Write Service and gateway.
local hmac_signature_mismatch = function()
    return kong.response.exit(401, {
        message = "Read-At-Least (RAL) header signature mismatch. Forbidden.",
    })
end


local exports = {
    malformed_header_message    = malformed_header_message,
    header_verification_failure = header_verification_failure,
    hmac_signature_mismatch     = hmac_signature_mismatch,
}

return exports
