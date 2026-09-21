local utilities    = require "kong.plugins.write-ral-version.utilities"
local redis_writer = require "kong.plugins.write-ral-version.redis_writer"

local WriteRalVersionHandler = {
    PRIORITY = 700,
    VERSION  = "0.2.0",
}


function WriteRalVersionHandler:header_filter(config)
    local raw_version = kong.response.get_header(config.write_version_header)
    if not raw_version or raw_version == "" then
        return
    end

    if not raw_version:match("^%d+$") then
        kong.log.warn("write-ral-version:", config.write_version_header,
            " is not a digit-only outbox seq: ", raw_version)
        return
    end

    local claims = kong.ctx.shared.clerk_claims
    local user_id = claims and claims.sub
    if not user_id then
        kong.log.warn("write-ral-version: no clerk sub in ctx; cannot record offset")
        return
    end

    local digest, digest_error = utilities.retrieve_digest(config.hmac_secret, raw_version)
    if not digest then
        kong.log.err("write-ral-version: failed signing ", config.write_version_header, ": ", digest_error)
        return
    end

    local signed = raw_version .. ":" .. utilities.to_hex(digest)
    kong.response.set_header(config.write_version_header, signed)

    kong.ctx.plugin.pending_offset_record = {
        user_id     = user_id,
        raw_version = raw_version,
    }
end


function WriteRalVersionHandler:log(config)
    local pending_record = kong.ctx.plugin.pending_offset_record
    if not pending_record then
        return
    end

    local redis_write, set_error = redis_writer.set_user_offset_monotonic(
        config, pending_record.user_id, pending_record.raw_version
    )
    if not redis_write then
        kong.log.warn("write-ral-version: redis offset update failed (best effort): ", set_error)
    end
end


return WriteRalVersionHandler
