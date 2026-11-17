local hmac          = require "resty.openssl.hmac"
local plugin_config = require "kong.plugins.demo-session.config"


local BASE64URL_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
local VERSION_PREFIX = plugin_config.DemoVisitIdentifierVersion .. "_"
local NONCE_START = #VERSION_PREFIX + 1
local NONCE_END = #VERSION_PREFIX + plugin_config.DemoVisitNonceLength
local EXPIRY_START = NONCE_END + 2
local EXPIRY_END = -(plugin_config.DemoVisitMacLength + 2)
local MINIMUM_IDENTIFIER_LENGTH = NONCE_END + 1 + 1 + 1 + plugin_config.DemoVisitMacLength


local encode_base64url = function(bytes)
    local encoded_characters = {}
    for group_start = 1, #bytes, 3 do
        local first_byte, second_byte, third_byte = bytes:byte(group_start, group_start + 2)
        local group_value = bit.bor(
            bit.lshift(first_byte, 16),
            bit.lshift(second_byte or 0, 8),
            third_byte or 0
        )
        local character_count = (second_byte == nil and 2) or (third_byte == nil and 3) or 4
        for character_position = 1, character_count do
            local sextet = bit.band(bit.rshift(group_value, (4 - character_position) * 6), 63)
            encoded_characters[#encoded_characters + 1] = BASE64URL_ALPHABET:sub(sextet + 1, sextet + 1)
        end
    end

    return table.concat(encoded_characters)
end


local constant_time_equals = function(first, second)
    if type(first) ~= "string" or type(second) ~= "string" or #first ~= #second then
        return false
    end

    local difference = 0
    for position = 1, #first do
        difference = bit.bor(difference, bit.bxor(first:byte(position), second:byte(position)))
    end

    return difference == 0
end


local is_base64url = function(candidate)
    return candidate:match("^[A-Za-z0-9_%-]+$") ~= nil
end


local parse_identifier = function(candidate_identifier)
    if type(candidate_identifier) ~= "string" then
        return nil
    end
    if #candidate_identifier < MINIMUM_IDENTIFIER_LENGTH
        or #candidate_identifier > plugin_config.DemoVisitIdentifierMaximumSize then
        return nil
    end
    if candidate_identifier:sub(1, #VERSION_PREFIX) ~= VERSION_PREFIX
        or candidate_identifier:sub(NONCE_END + 1, NONCE_END + 1) ~= "_"
        or candidate_identifier:sub(EXPIRY_END + 1, EXPIRY_END + 1) ~= "_" then
        return nil
    end

    local nonce = candidate_identifier:sub(NONCE_START, NONCE_END)
    local encoded_expiry = candidate_identifier:sub(EXPIRY_START, EXPIRY_END)
    local mac = candidate_identifier:sub(-plugin_config.DemoVisitMacLength)

    if not is_base64url(nonce) or not is_base64url(mac) then
        return nil
    end
    if #encoded_expiry > plugin_config.DemoVisitExpiryMaximumLength
        or encoded_expiry:match("^[0-9a-z]+$") == nil then
        return nil
    end

    return {
        nonce          = nonce,
        encoded_expiry = encoded_expiry,
        expires_at     = tonumber(encoded_expiry, 36),
        mac            = mac,
    }
end


local sign = function(secret, nonce, encoded_expiry)
    local hmac_signer, signer_error = hmac.new(secret, "sha256")
    if not hmac_signer then
        return nil, "hmac init: " .. tostring(signer_error)
    end

    local signed_payload = plugin_config.DemoVisitIdentifierVersion .. "." .. nonce .. "." .. encoded_expiry
    local digest, digest_error = hmac_signer:final(signed_payload)
    if not digest then
        return nil, "hmac final: " .. tostring(digest_error)
    end

    return encode_base64url(digest:sub(1, plugin_config.DemoVisitMacBytes)), nil
end


local verify = function(secret, candidate_identifier, current_unix_seconds)
    if type(secret) ~= "string" or secret == "" then
        return nil, "no demo session secret is configured"
    end

    local parsed_identifier = parse_identifier(candidate_identifier)
    if not parsed_identifier then
        return nil, "malformed identifier"
    end

    local expected_mac, signing_error = sign(secret, parsed_identifier.nonce, parsed_identifier.encoded_expiry)
    if not expected_mac then
        return nil, signing_error
    end
    if not constant_time_equals(expected_mac, parsed_identifier.mac) then
        return nil, "signature mismatch"
    end
    if parsed_identifier.expires_at <= current_unix_seconds then
        return nil, "expired"
    end

    return {
        nonce      = parsed_identifier.nonce,
        expires_at = parsed_identifier.expires_at,
    }, nil
end


return {
    encode_base64url     = encode_base64url,
    constant_time_equals = constant_time_equals,
    parse_identifier     = parse_identifier,
    sign                 = sign,
    verify               = verify,
}
