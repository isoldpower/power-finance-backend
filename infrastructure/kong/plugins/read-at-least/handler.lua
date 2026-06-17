-- Custom Kong plugin: read-at-least
--
-- Implements the request-side mechanics for the Read-At-Least header.
-- The response side (signing X-Write-Version on write routes and
-- recording the per-user offset to Redis) lives in the separate
-- `write-ral-version` plugin so the read and write halves can be
-- attached to their own routes without cross-coupling.
--
--   * When the client supplies a Read-At-Least header, validate it as
--     `<offset>:<hex-hmac-sha256>` against a gateway-internal secret.
--     This stops clients from forging arbitrary offsets to force
--     Read-Service 503 fallbacks.
--
--   * When the client omits Read-At-Least, look up the user's latest
--     write offset in Redis (key `ral:user:{sub}`, populated by the
--     write-ral-version plugin on write responses) and inject a freshly
--     signed header. Falls open (no header, free read) on Redis miss
--     or any lookup failure.
--
-- "Offset" here is the Postgres outbox seq id (BIGSERIAL), not the
-- Kafka offset — see write-ral-version/redis_writer.lua for how the value
-- gets into Redis.
--
-- Runs AFTER clerk-jwt so kong.ctx.shared.clerk_claims is populated.

local messages     = require "kong.plugins.read-at-least.messages"
local utilities    = require "kong.plugins.read-at-least.utilities"
local redis_lookup = require "kong.plugins.read-at-least.redis_lookup"

-- PRIORITY 700 keeps read-at-least below clerk-jwt (801) so the verified
-- claims have already been stashed in kong.ctx.shared by the time this
-- runs.
local ReadAtLeastHandler = {
    PRIORITY = 700,
    VERSION  = "0.5.0",
}

local READ_AT_LEAST_HEADER = "Read-At-Least"


local verify_received_header = function(config, header)
    local offset, signature = header:match("^(%d+):([a-fA-F0-9]+)$")
    if not offset or not signature then
        return messages.malformed_header_message()
    end

    local digest, digest_error = utilities.retrieve_digest(config.hmac_secret, offset)
    if not digest then
        kong.log.err("read-at-least: ", digest_error)
        return messages.header_verification_failure()
    end
    local hex_digest = utilities.to_hex(digest)

    if not utilities.constant_time_equals(hex_digest, signature:lower()) then
        return messages.hmac_signature_mismatch()
    end

    return nil
end


local sign_default_offset = function(config, user_id)
    local offset, lookup_error = redis_lookup.get_user_offset(config, user_id)
    if lookup_error then
        kong.log.warn("read-at-least: redis lookup failed (failing open): ", lookup_error)
        return nil
    end
    if not offset then
        return nil
    end

    local digest, digest_error = utilities.retrieve_digest(config.hmac_secret, offset)
    if not digest then
        kong.log.err("read-at-least: ", digest_error)
        return nil
    end

    return {
        signature = utilities.to_hex(digest),
        offset    = offset,
    }
end


function ReadAtLeastHandler:access(config)
    local header = kong.request.get_header(READ_AT_LEAST_HEADER)
    if header and header ~= "" then
        return verify_received_header(config, header)
    end

    local claims = kong.ctx.shared.clerk_claims
    if not claims or not claims.sub then
        return
    end

    local stored_state = sign_default_offset(config, claims.sub)
    if stored_state then
        local header_value = stored_state.offset .. ":" .. stored_state.signature
        kong.service.request.set_header(READ_AT_LEAST_HEADER, header_value)
    end
end


return ReadAtLeastHandler
