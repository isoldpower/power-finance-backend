-- Custom Kong plugin: read-at-least
--
-- Implements the gateway-side mechanics for the Read-At-Least header
-- described in the architecture spec:
--
--   * When the client supplies a Read-At-Least header, validate it as
--     `<offset>:<hex-hmac-sha256>` against a secret shared with the
--     Write Service. This stops clients from forging arbitrary offsets
--     to force Read-Service 503 fallbacks.
--
--   * When the client omits Read-At-Least, look at the Clerk JWT claim
--     `last_write_offset` (or whatever name `offset_claim_name` points
--     at) and inject a freshly-signed header. The Write Service can
--     bake the latest offset into the session token on every refresh,
--     so reads are read-your-writes by default without the client
--     having to keep track.
--
-- Runs AFTER clerk-jwt so kong.ctx.shared.clerk_claims is populated.

local hmac = require "resty.openssl.hmac"

-- PRIORITY 700 keeps read-at-least below clerk-jwt (850) so the verified
-- claims have already been stashed in kong.ctx.shared by the time this
-- runs.
local ReadAtLeastHandler = {
    PRIORITY = 700,
    VERSION  = "0.2.0",
}

local READ_AT_LEAST_HEADER = "Read-At-Least"


local function unauthorized(message)
    return kong.response.exit(401, { message = message })
end


local function to_hex(bytes)
    return (bytes:gsub(".", function(c) return string.format("%02x", c:byte()) end))
end


local function sign(secret, payload)
    local h, err = hmac.new(secret, "sha256")
    if not h then
        return nil, "hmac init: " .. (err or "unknown")
    end
    local digest, derr = h:final(payload)
    if not digest then
        return nil, "hmac final: " .. (derr or "unknown")
    end
    return to_hex(digest)
end


-- Constant-time string equality. Required for HMAC verification — a naive
-- `==` leaks timing information about the prefix length of the matching
-- signature and lets an attacker recover the secret one byte at a time.
local function constant_time_equals(a, b)
    if type(a) ~= "string" or type(b) ~= "string" or #a ~= #b then
        return false
    end
    local diff = 0
    for i = 1, #a do
        diff = bit.bor(diff, bit.bxor(a:byte(i), b:byte(i)))
    end
    return diff == 0
end


function ReadAtLeastHandler:access(conf)
    local header = kong.request.get_header(READ_AT_LEAST_HEADER)

    if header and header ~= "" then
        local offset, signature = header:match("^(%d+):([a-fA-F0-9]+)$")
        if not offset or not signature then
            return unauthorized("Malformed Read-At-Least header.")
        end

        local expected, err = sign(conf.hmac_secret, offset)
        if not expected then
            kong.log.err("read-at-least: ", err)
            return unauthorized("Read-At-Least verification failed.")
        end
        if not constant_time_equals(expected, signature:lower()) then
            return unauthorized("Read-At-Least signature mismatch.")
        end
        -- Header is trusted — leave it untouched for the upstream.
        return
    end

    -- No header → try to inject from the JWT default offset claim.
    local claims = kong.ctx.shared.clerk_claims
    if not claims then
        return
    end
    local claim_value = claims[conf.offset_claim_name]
    if claim_value == nil then
        return
    end

    local offset = tostring(claim_value)
    if not offset:match("^%d+$") then
        kong.log.warn(
            "read-at-least: JWT claim `", conf.offset_claim_name,
            "` is not an integer offset; skipping injection"
        )
        return
    end

    local signature, err = sign(conf.hmac_secret, offset)
    if not signature then
        kong.log.err("read-at-least: ", err)
        return
    end
    kong.service.request.set_header(READ_AT_LEAST_HEADER, offset .. ":" .. signature)
end


return ReadAtLeastHandler
