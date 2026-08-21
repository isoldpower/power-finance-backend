-- Custom Kong plugin: user-tier-rate-limit
--
-- Per-user rate limit applied on top of the IP floor. Runs after clerk-jwt
-- so the verified `sub` claim is available — no claims means the request
-- is anonymous and this plugin is a no-op (the IP floor still applies).
--
-- Why custom: Kong's bundled rate-limiting plugin can only have one
-- instance per scope. We need the IP floor (built-in) AND a per-user
-- ceiling at the same time, so the user tier needs to be a separate
-- plugin class. Uses SLIDING WINDOW strategy. Failure modes are fail-open.

local messages      = require "kong.plugins.user-tier-rate-limit.messages"
local redis_counter = require "kong.plugins.user-tier-rate-limit.redis_counter"


-- PRIORITY 600 keeps user-tier-rate-limit below clerk-jwt (801) so the
-- verified claims have already been stashed in kong.ctx.shared by the
-- time this runs.
local UserTierRateLimitHandler = {
    PRIORITY = 600,
    VERSION  = "0.3.0",
}


-- Window definitions. Adding a new window (e.g. per-second burst, per-day
-- quota) is a matter of pushing one more row here — the counter and the script
-- both loop over whatever this table holds.
local WINDOWS = {
    { label = "minute", seconds = 60,   header_suffix = "Minute", config_key = "per_minute" },
    { label = "hour",   seconds = 3600, header_suffix = "Hour",   config_key = "per_hour" },
}


--- Set the `X-RateLimit-{Limit,Remaining}-{window}` response headers.
-- Mirrors the shape used by Kong's bundled rate-limiting plugin so
-- clients see one consistent header family regardless of which tier
-- bound their traffic.
--
-- @param evaluated_window table  one row of the counter's reply
local set_window_headers = function(evaluated_window)
    local remaining = evaluated_window.limit - evaluated_window.estimate

    kong.response.set_header(
        "X-RateLimit-Limit-" .. evaluated_window.header_suffix,
        evaluated_window.limit
    )
    kong.response.set_header(
        "X-RateLimit-Remaining-" .. evaluated_window.header_suffix,
        math.max(0, remaining)
    )
end


--- How long until this window would admit one more request, assuming the
-- caller stops sending in the meantime.
--
-- @param evaluated_window table  one row of the counter's reply
-- @return number  whole seconds to wait, at least 1
local seconds_until_admitted = function(evaluated_window)
    local headroom = evaluated_window.limit - evaluated_window.current
    local previous = evaluated_window.previous

    if headroom > 0 and previous > 0 then
        local decayed_at = evaluated_window.seconds
            - (headroom * evaluated_window.seconds / previous)

        return math.max(1, math.ceil(decayed_at - evaluated_window.elapsed))
    end

    return math.max(1, math.ceil(evaluated_window.seconds - evaluated_window.elapsed))
end


--- Longest wait across the windows that rejected the request.
-- Backing off for the shorter one would only trip the longer one again.
local retry_after_seconds = function(evaluated)
    local retry_after = 1

    for _, evaluated_window in ipairs(evaluated.windows) do
        if evaluated_window.estimate > evaluated_window.limit then
            retry_after = math.max(retry_after, seconds_until_admitted(evaluated_window))
        end
    end

    return retry_after
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

    local evaluated, evaluate_error = redis_counter.evaluate_windows(
        client, config, claims.sub, WINDOWS
    )
    redis_counter.release(client)

    if not evaluated then
        kong.log.warn("user-tier-rate-limit: ", evaluate_error, " — failing open")
        return
    end

    for _, evaluated_window in ipairs(evaluated.windows) do
        set_window_headers(evaluated_window)
    end

    if not evaluated.allowed then
        return messages.rate_limit_exceeded(retry_after_seconds(evaluated))
    end
end


return UserTierRateLimitHandler
