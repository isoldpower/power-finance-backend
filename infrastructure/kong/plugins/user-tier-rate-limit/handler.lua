-- Custom Kong plugin: user-tier-rate-limit
--
-- Per-user rate limit applied on top of the IP floor. Runs after clerk-jwt
-- so the verified `sub` claim is available — no claims means the request
-- is anonymous and this plugin is a no-op (the IP floor still applies).
--
-- Why custom: Kong's bundled rate-limiting plugin can only have one
-- instance per scope. We need the IP floor (built-in) AND a per-user
-- ceiling at the same time, so the user tier needs to be a separate
-- plugin class.
--
-- Counter strategy: fixed minute/hour windows in Redis via INCR + EXPIRE.
-- Cheaper and simpler than a sliding window; accuracy at window edges is
-- fine for fraud/abuse prevention.
--
-- Failure modes are fail-open: any Redis error logs a warning and the
-- request proceeds without counting. The IP floor still bounds the
-- blast radius if Redis is down.

local messages      = require "kong.plugins.user-tier-rate-limit.messages"
local redis_counter = require "kong.plugins.user-tier-rate-limit.redis_counter"

-- PRIORITY 600 keeps user-tier-rate-limit below clerk-jwt (801) so the
-- verified claims have already been stashed in kong.ctx.shared by the
-- time this runs.
local UserTierRateLimitHandler = {
    PRIORITY = 600,
    VERSION  = "0.2.0",
}


-- Window definitions. Adding a new window (e.g. per-second burst, per-day
-- quota) is a matter of pushing one more row here — the loop below picks
-- it up automatically.
local WINDOWS = {
    { label = "minute", seconds = 60,   header_suffix = "Minute", config_key = "per_minute" },
    { label = "hour",   seconds = 3600, header_suffix = "Hour",   config_key = "per_hour" },
}


--- Set the `X-RateLimit-{Limit,Remaining}-{window}` response headers.
-- Mirrors the shape used by Kong's bundled rate-limiting plugin so
-- clients see one consistent header family regardless of which tier
-- bound their traffic.
--
-- @param header_suffix string  the "Minute" / "Hour" tail of the header name
-- @param limit number  configured ceiling for the window
-- @param remaining number  budget left after the current request
local set_window_headers = function(header_suffix, limit, remaining)
    kong.response.set_header("X-RateLimit-Limit-" .. header_suffix, limit)
    kong.response.set_header("X-RateLimit-Remaining-" .. header_suffix, math.max(0, remaining))
end


--- Increment counters across all windows and return whether any were
-- exceeded. On the first Redis error we fail open: stop counting,
-- release the connection, and let the request through.
--
-- @param client table  resty.redis client
-- @param config table  plugin config record
-- @param user_id string  Clerk `sub` claim
-- @return boolean  true if any window's post-increment count exceeds its limit
local apply_all_windows = function(client, config, user_id)
    local any_exceeded = false

    for _, window in ipairs(WINDOWS) do
        local limit = config[window.config_key]
        local count, increment_error = redis_counter.increment_window(
            client, config.redis_key_prefix, user_id, window.label, window.seconds
        )
        if not count then
            kong.log.warn("user-tier-rate-limit: ", increment_error, " — failing open")
            return false
        end

        set_window_headers(window.header_suffix, limit, limit - count)
        if count > limit then
            any_exceeded = true
        end
    end

    return any_exceeded
end


function UserTierRateLimitHandler:access(config)
    local claims = kong.ctx.shared.clerk_claims
    if not claims or not claims.sub or claims.sub == "" then
        return
    end

    local client, connect_error = redis_counter.connect_to_redis(config)
    if not client then
        kong.log.warn("user-tier-rate-limit: ", connect_error, " — failing open")
        return
    end

    local exceeded = apply_all_windows(client, config, claims.sub)
    redis_counter.release(client)

    if exceeded then
        return messages.rate_limit_exceeded()
    end
end


return UserTierRateLimitHandler
