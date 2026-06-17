local hmac = require "resty.openssl.hmac"


--- Encode a binary string as lowercase hexadecimal.
-- Output length is exactly 2× input length. Used to render an HMAC
-- digest into the over-the-wire `{seq}:{hex}` form clients see.
--
-- @param bytes string  arbitrary binary input
-- @return string  lowercase hex encoding
local to_hex = function(bytes)
    return (bytes:gsub(".", function(c) return string.format("%02x", c:byte()) end))
end


--- Compute an HMAC-SHA256 digest over `payload` using `secret`.
-- Returns the raw (binary) digest; callers that need the on-the-wire
-- representation should pipe the result through `to_hex`.
--
-- @param secret string  shared HMAC key
-- @param payload string  message to sign
-- @return string|nil  raw HMAC-SHA256 digest on success
-- @return string|nil  error message on failure
local retrieve_digest = function(secret, payload)
    local hmac_signed, sign_error = hmac.new(secret, "sha256")
    if not hmac_signed then
        return nil, "hmac init: " .. (sign_error or "Unknown Error")
    end

    local digest, digest_error = hmac_signed:final(payload)
    if not digest then
        return nil, "hmac final: " .. (digest_error or "Unknown Error")
    end

    return digest, nil
end


local exports = {
    to_hex          = to_hex,
    retrieve_digest = retrieve_digest,
}

return exports
