local hmac = require "resty.openssl.hmac"


--- Encode a binary string as lowercase hexadecimal.
--
-- @param bytes string  arbitrary binary input
-- @return string  lowercase hex encoding
local to_hex = function(bytes)
    return (bytes:gsub(".", function(c) return string.format("%02x", c:byte()) end))
end


--- Compute an HMAC-SHA256 digest over `payload` using `secret`.
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


--- Compare two strings in constant time relative to their length.
--
-- @param first string
-- @param second string
-- @return boolean  true iff inputs are byte-equal
local constant_time_equals = function(first, second)
    if type(first) ~= "string" or type(second) ~= "string" or #first ~= #second then
        return false
    end

    local diff = 0
    for i = 1, #first do
        diff = bit.bor(diff, bit.bxor(first:byte(i), second:byte(i)))
    end

    return diff == 0
end


local exports = {
    to_hex               = to_hex,
    retrieve_digest      = retrieve_digest,
    constant_time_equals = constant_time_equals,
}

return exports
